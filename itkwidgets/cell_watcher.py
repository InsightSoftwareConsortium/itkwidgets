import asyncio
import sys
from inspect import isawaitable, iscoroutinefunction
from IPython import get_ipython
from queue import Queue
from imjoy_rpc.utils import FuturePromise

background_tasks = set()


class Viewers(object):
    def __init__(self):
        self._data = {}

    @property
    def data(self):
        return self._data

    @property
    def not_created(self):
        # Return a list of names of viewers that have not been created yet
        names = []
        for key, val in self.data.items():
            name = val['name']
            if not val['status']:
                name = name if name is not None else key
                names.append(name)
        return names

    @property
    def not_named(self):
        # Return a list of names of viewers that have not been named yet
        return any([k for k, v in self.data.items() if v['name'] is None])

    @property
    def viewer_objects(self):
        # Return a list of created viewers
        return list(self.data.keys())

    def add_viewer(self, view):
        self.data[view] = {'name': None, 'status': False}

    def set_name(self, view, name):
        if view not in self.data.keys():
            self.add_viewer(view)
        self.data[view]['name'] = name

    def update_viewer_status(self, view, status):
        if view not in self.data.keys():
            self.add_viewer(view)
        self.data[view]['status'] = status

    def viewer_ready(self, view):
        if viewer := self.data.get(view):
            return viewer['status']
        return False


class CellWatcher(object):
    def __new__(cls):
        if not hasattr(cls, '_instance'):
            cls._instance = super(CellWatcher, cls).__new__(cls)
            cls._instance.setup()
        return cls._instance

    def setup(self):
        self.viewers = Viewers()
        self.shell = get_ipython()
        self.kernel = self.shell.kernel
        self.shell_stream = getattr(self.kernel, "shell_stream", None)
        self.execute_request_handler = self.kernel.shell_handlers["execute_request"]
        # Keep a reference to the ipykernel execute_request function
        self.current_request = None
        self.waiting_on_viewer = False
        self.results = {}
        self.abort_all = False

        self._events = Queue()

        # Replace the ipykernel shell_handler for execute_request with our own
        # function, which we can use to capture, queue and process future cells
        if iscoroutinefunction(self.execute_request_handler):  # ipykernel 6+
            self.kernel.shell_handlers["execute_request"] = self.capture_event_async
        else:
            # ipykernel < 6
            self.kernel.shell_handlers["execute_request"] = self.capture_event

        # Call self.post_run_cell every time the post_run_cell signal is emitted
        # post_run_cell runs after interactive execution (e.g. a cell in a notebook)
        self.shell.events.register('post_run_cell', self.post_run_cell)

    def add_viewer(self, view):
        # Track all Viewer instances
        self.viewers.add_viewer(view)

    def update_viewer_status(self, view, status):
        self.viewers.update_viewer_status(view, status)
        if self.waiting_on_viewer:
            # Might be ready now, try again
            self.create_task(self.execute_next_request)

    def viewer_ready(self, view):
        return self.viewers.viewer_ready(view)

    def _task_cleanup(self, task):
        global background_tasks
        try:
            # "Handle" exceptions here to prevent further errors. Exceptions
            # thrown will be actually be raised in the Viewer._fetch_value
            # decorator.
            _ = task.exception()
        except:
            background_tasks.discard(task)

    def create_task(self, fn):
        global background_tasks
        # The event loop only keeps weak references to tasks.
        # Gather them into a set to avoid garbage collection mid-task.
        task = asyncio.create_task(fn())
        background_tasks.add(task)
        task.add_done_callback(self._task_cleanup)

    def capture_event(self, stream, ident, parent):
        self._events.put((stream, ident, parent))
        if self._events.qsize() == 1 and self.ready_to_run_next_cell():
            # We've added a new task to an empty queue.
            # Begin executing tasks again.
            self.create_task(self.execute_next_request)

    async def capture_event_async(self, stream, ident, parent):
        # ipykernel 6+
        self.capture_event(stream, ident, parent)

    @property
    def all_getters_resolved(self):
        # Check if all of the getter/setter futures have resolved
        getters_resolved = [f.done() for f in self.results.values()]
        return all(getters_resolved)

    def ready_to_run_next_cell(self):
        # Any itk_viewer objects need to be available and all getters/setters
        # need to be resolved
        self.waiting_on_viewer = len(self.viewers.not_created)
        return self.all_getters_resolved and not self.waiting_on_viewer

    async def execute_next_request(self):
        # Modeled after the approach used in jupyter-ui-poll
        # https://github.com/Kirill888/jupyter-ui-poll/blob/f65b81f95623c699ed7fd66a92be6d40feb73cde/jupyter_ui_poll/_poll.py#L75-L101
        if self._events.empty():
            self.abort_all = False

        if self.current_request is None and not self._events.empty():
            # Fetch the next request if we haven't already
            self.current_request = self._events.get()

        if self.ready_to_run_next_cell():
            # Continue processing the remaining queued tasks
            await self._execute_next_request()

    async def _execute_next_request(self):
        # Here we actually run the queued cell as it would have been run
        stream, ident, parent = self.current_request

        # Set I/O to the correct cell
        self.kernel.set_parent(ident, parent)
        if self.abort_all or self.kernel._aborting:
            self.kernel._send_abort_reply(stream, parent, ident)
        else:
            # Use the original kernel execute_request method to run the cell
            rr = self.execute_request_handler(stream, ident, parent)
            if isawaitable(rr):
                rr = await rr

            # Make sure we print all output to the correct cell
            sys.stdout.flush()
            sys.stderr.flush()
            if self.shell_stream is not None:
                # ipykernel 6
                self.kernel._publish_status("idle", "shell")
                self.shell_stream.flush(2)
            else:
                self.kernel._publish_status("idle")

        self.current_request = None
        if self.all_getters_resolved:
            # Continue processing the remaining queued tasks
            self.create_task(self.execute_next_request)

    def update_namespace(self):
        # Update the namespace variables with the results from the getters
        # FIXME: This is a temporary "fix" and does not handle updating output
        keys = [k for k in self.shell.user_ns.keys()]
        for key in keys:
            value = self.shell.user_ns[key]
            if asyncio.isfuture(value) and (isinstance(value, FuturePromise) or isinstance(value, asyncio.Task)):
                # Getters/setters return futures
                # They should all be resolved now, so use the result
                self.shell.user_ns[key] = value.result()
        self.results.clear()

    def _callback(self, *args, **kwargs):
        # After each getter/setter resolves check if they've all resolved
        if self.all_getters_resolved:
            self.update_namespace()
            self.create_task(self.execute_next_request)

    def find_view_object_names(self):
        from .viewer import Viewer
        # Used to determine that all references to Viewer
        # objects are ready before a cell is run
        objs = self.viewers.viewer_objects
        user_vars = [k for k in self.shell.user_ns.keys() if not k.startswith('_')]
        for var in user_vars:
            # Identify which variable the view object has been assigned to
            value = self.shell.user_ns[var]
            if isinstance(value, Viewer) and value.__str__() in objs:
                idx = objs.index(value.__str__())
                self.viewers.set_name(objs[idx], var)

    def post_run_cell(self, response):
        # If a cell has been run and there are viewers with no variable
        # associated with them check the user namespace to see if they have
        # been added
        if response.error_in_exec is not None:
            self.abort_all = True
        if self.viewers.not_named:
            self.find_view_object_names()
