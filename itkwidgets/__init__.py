from ._version import version_info, __version__

from .widget_viewer import Viewer, view

def _jupyter_nbextension_paths():
    return [{
        'section': 'notebook',
        'src': 'static',
        'dest': 'itk-jupyter-widgets',
        'require': 'itk-jupyter-widgets/extension'
    }]
