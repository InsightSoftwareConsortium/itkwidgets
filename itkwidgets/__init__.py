from ._version import version_info, __version__

from .widget_viewer import Viewer, view
from .widget_checkerboard import checkerboard
from .widget_line_profiler import line_profile
from . import cm

def _jupyter_nbextension_paths():
    return [{
        'section': 'notebook',
        'src': 'static',
        'dest': 'itkwidgets',
        'require': 'itkwidgets/extension'
    }]
