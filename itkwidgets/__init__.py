__all__ = ['version_info', '__version__',
           'Viewer', 'view',
           'checkerboard',
           'compare',
           'line_profile',
           'label_statistics',
           'cm',
           'lut',
           '_jupyter_nbextension_paths']

from ._version import version_info, __version__

from .widget_viewer import Viewer, view
from .widget_compare import compare
from .widget_checkerboard import checkerboard
from .widget_line_profiler import line_profile
from .widget_label_statistics import label_statistics
from . import cm, lut


def _jupyter_nbextension_paths():
    return [{
        'section': 'notebook',
        'src': 'static',
        'dest': 'itkwidgets',
        'require': 'itkwidgets/extension'
    }]
