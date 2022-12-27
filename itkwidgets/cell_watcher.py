import asyncio
import sys
from inspect import isawaitable, iscoroutinefunction
import uuid
from IPython import get_ipython
from queue import Queue

background_tasks = set()

class CellWatcher(object):
    def __init__(self, viewer):
        self.viewer = viewer
        self.view_object = None
        self.shell = get_ipython()
        self.kernel = self.shell.kernel
        self.shell_stream = getattr(self.kernel, "shell_stream", None)
        self.execute_request_handler = self.kernel.shell_handlers["execute_request"]
        self.current_request = None
        self.itk_viewer_created = False
        self.results = {}

        self._events = Queue()

        if iscoroutinefunction(self.execute_request_handler):  # ipykernel 6+
            self.kernel.shell_handlers["execute_request"] = self.capture_event_async
        else:
            # ipykernel < 6
            self.kernel.shell_handlers["execute_request"] = self.capture_event

        self.shell.events.register('post_run_cell', self.post_run_cell)
        self.shell.events.register('pre_execute', self.pre_execute)

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
        # Gather them in a collection to avoid garbage collection mid-task.
        task = asyncio.create_task(fn())
        background_tasks.add(task)
        task.add_done_callback(self._task_cleanup)

    def capture_event(self, stream, ident, parent):
        self._events.put((stream, ident, parent))
        if self.itk_viewer_created and self._events.qsize() == 1:
            # We've added a new task to an empty queue.
            # Begin executing tasks again.
            self.create_task(self.execute_next_request)

    async def capture_event_async(self, stream, ident, parent):
        # ipykernel 6+
        self.capture_event(stream, ident, parent)

    @property
    def all_getters_resolved(self):
        getters_resolved = [f.done() for f in self.results.values()]
        return all(getters_resolved)

    async def execute_next_request(self):
        # Modeled after the approach used in jupyter-ui-poll
        # https://github.com/Kirill888/jupyter-ui-poll/blob/f65b81f95623c699ed7fd66a92be6d40feb73cde/jupyter_ui_poll/_poll.py#L75-L101
        if self._events.empty():
            return

        # Fetch the next request
        stream, ident, parent = self._events.get()

        # Set I/O to the correct cell
        self.kernel.set_parent(ident, parent)
        if self.kernel._aborting:
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
        keys = [k for k in self.shell.user_ns.keys()]
        for key in keys:
            value = self.shell.user_ns[key]
            if isinstance(value, uuid.UUID) and value in self.results:
                self.shell.user_ns[key] = self.results[value].result()
        self.results.clear()

    def _callback(self, name=None, future=None):
        if name is not None and future is not None:
            self.results[name].set_result(future.result())
        else:
            self.results.clear()
        # if all getters have resolved then ready to re-run
        if self.all_getters_resolved:
            self.update_namespace()
            self.create_task(self.execute_next_request)

    def pre_execute(self):
        if not self.itk_viewer_created and self.viewer.has_viewer:
            # The viewer exists, we can begin processing cells
            self.itk_viewer_created = self.viewer.has_viewer
            self.create_task(self.execute_next_request)

    def find_view_object(self):
        # Used to identify getter functions and associate them
        # with the appropriate view instance
        user_vars = [k for k in self.shell.user_ns.keys() if not k.startswith('_')]
        for var in user_vars:
            # Identify which variable the view object has been assigned to
            value = self.shell.user_ns[var]
            if type(value) == type(self.viewer) and value == self.viewer:
                self.view_object = var

    def post_run_cell(self):
        if self.view_object is None:
            self.find_view_object()
