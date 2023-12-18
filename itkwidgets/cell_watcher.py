import asyncio
import sys
from inspect import isawaitable, iscoroutinefunction
from typing import Dict, List
from IPython import get_ipython
from queue import Queue
from imjoy_rpc.utils import FuturePromise

background_tasks = set()


class Viewers(object):
    """This class is designed to track each instance of the Viewer class that
    is instantiated as well as whether or not that instance is available for
    updates or requests.
    """
    def __init__(self):
        self._data = {}

    @property
    def data(self) -> Dict[str, Dict[str, bool]]:
        """Get the underlying data dict containg all viewer data

        :return: The data object that contains all created Viewer information.
        :rtype:  Dict[str, Dict[str, bool]]
        """
        return self._data

    @property
    def not_created(self) -> List[str]:
        """Return a list of all unavailable viewers

        :return: A list of names of viewers that have not yet been created.
        :rtype:  List[str]
        """
        return [k for k in self.data.keys() if not self.viewer_ready(k)]

    def add_viewer(self, view: str) -> None:
        """Add a new Viewer object to track.

        :param view: The unique string identifier for the Viewer object
        :type view:  str
        """
        self.data[view] = {"ready": False}

    def update_viewer_status(self, view: str, status: bool) -> None:
        """Update a Viewer's 'ready' status.

        :param view: The unique string identifier for the Viewer object
        :type view:  str
        :param status: Boolean value indicating whether or not the viewer is
        available for requests or updates. This should be false when the plugin
        API is not yet available or new data is not yet rendered.
        :type status:  bool
        """
        if view not in self.data.keys():
            self.add_viewer(view)
        self.data[view]["ready"] = status

    def viewer_ready(self, view: str) -> bool:
        """Request the 'ready' status of a viewer.

        :param view: The unique string identifier for the Viewer object
        :type view:  str

        :return: Boolean value indicating whether or not the viewer is
        available for requests or updates. This will be false when the plugin
        API is not yet available or new data is not yet rendered.
        :rtype:  bool
        """
        return self.data.get(view, {}).get("ready", False)


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
        # Keep a reference to the ipykernel execute_request function
        self.execute_request_handler = self.kernel.shell_handlers["execute_request"]
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

        if not self.results:
            self.current_request = None
        if self.all_getters_resolved and not self._events.empty():
            # Continue processing the remaining queued tasks
            self.create_task(self.execute_next_request)

    def update_namespace(self):
        # Update the namespace variables with the results from the getters
        # FIXME: This is a temporary "fix" and does not handle updating output
        keys = [k for k in self.shell.user_ns.keys()]
        try:
            for key in keys:
                value = self.shell.user_ns[key]
                if asyncio.isfuture(value) and (isinstance(value, FuturePromise) or isinstance(value, asyncio.Task)):
                    # Getters/setters return futures
                    # They should all be resolved now, so use the result
                    self.shell.user_ns[key] = value.result()
            self.results.clear()
        except Exception as e:
            self.results.clear()
            self.abort_all = True
            self.create_task(self._execute_next_request)
            raise e

    def _callback(self, *args, **kwargs):
        # After each getter/setter resolves check if they've all resolved
        if self.all_getters_resolved:
            self.update_namespace()
            self.current_request = None
            self.create_task(self.execute_next_request)

    def post_run_cell(self, response):
        # Abort remaining cells on error in execution
        if response.error_in_exec is not None:
            self.abort_all = True
