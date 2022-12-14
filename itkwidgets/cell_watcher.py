from IPython import get_ipython

background_tasks = set()

class CellWatcher(object):
    def __init__(self):
        self.ip = get_ipython()
        self.ip.events.register('pre_run_cell', self.pre_run_cell)

    def pre_run_cell(self, info):
        # grab info for rerun
        self.raw = info.raw_cell
        self.id = info.cell_id

    def _callback(self, name, future):
        self.results[name].set_result(future.result())
        getters_resolved = [f.done() for f in self.results.values()]
        # if all getters have resolved then ready to rerun
        if all(getters_resolved):
            self.ip.run_cell(raw_cell=self.raw, cell_id=self.id)
