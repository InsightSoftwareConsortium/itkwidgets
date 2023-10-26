"""itkwidgets: an elegant Python interface for visualization on the web platform
to interactively generate insights into multidimensional images, point sets, and geometry."""
from .integrations.environment import ENVIRONMENT, Env

if ENVIRONMENT is not Env.HYPHA:
    from imjoy_rpc import register_default_codecs
    register_default_codecs()

    from .imjoy import register_itkwasm_imjoy_codecs
    register_itkwasm_imjoy_codecs()

from .viewer import Viewer, view, compare_images
from .standalone_server import standalone_viewer

__all__ = [
  "Viewer",
  "view",
  "compare_images",
  "standalone_viewer",
]
