import asyncio
import re
import sys
from inspect import isawaitable, iscoroutinefunction
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

    def preprocess_getters(self, raw):
        regex = f"{self.view_object}.get_(.*)\([^()]*\)"
        lines = raw.split('\n')
        # Find and evaluate any getters in the cell before the cell
        # is actually run
        count = 0
        for line in lines:
            if not line.startswith('#'):
                res = [self.shell.ev(m.group()) for m in re.finditer(regex, line)]
                count += len(res)
        return count

    async def execute_next_request(self):
        if self._events.empty():
            return

        self.current_request = self._events.get()
        raw = self.current_request[2]["content"].get("code", "")
        getters = self.preprocess_getters(raw)
        if getters == 0:
            # If there are no getters, process the cell as usual
            await self._execute_next_request()

    async def _execute_next_request(self):
        # Modeled after the approach used in jupyter-ui-poll
        # https://github.com/Kirill888/jupyter-ui-poll/blob/f65b81f95623c699ed7fd66a92be6d40feb73cde/jupyter_ui_poll/_poll.py#L75-L101

        # Fetch the next request
        stream, ident, parent = self.current_request

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
        # Continue processing the remaining queued tasks
        self.create_task(self.execute_next_request)

    def _callback(self, name=None, future=None):
        if name is not None and future is not None:
            self.viewer.results[name].set_result(future.result())
            getters_resolved = [f.done() for f in self.viewer.results.values()]
        else:
            getters_resolved = [True]
        # if all getters have resolved then ready to re-run
        if all(getters_resolved):
            self.create_task(self._execute_next_request)

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
