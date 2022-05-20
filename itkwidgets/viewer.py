__all__ = [
  "Viewer",
]

class Viewer:
  """Viewer class."""

  def __init__(self, **kwargs):
      try:
          from google.colab import output
          self.running_in_colab = True
      except ModuleNotFoundError:
          self.running_in_colab = False
      self.image = kwargs.get('image', None)

  async def setup(self):
      if self.running_in_colab:
          viewer = await api.showDialog(
              type='itk-vtk-viewer',
              src='https://kitware.github.io/itk-vtk-viewer/app',
          )
      else:
          viewer = await api.createWindow(
              type='itk-vtk-viewer',
              src='https://kitware.github.io/itk-vtk-viewer/app',
          )
      await viewer.setImage(self.image)