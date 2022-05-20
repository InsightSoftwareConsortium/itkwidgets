from .viewer import Viewer

__all__ = [
  "view",
]

def view(image=None):
    return api.export(Viewer(image=image))