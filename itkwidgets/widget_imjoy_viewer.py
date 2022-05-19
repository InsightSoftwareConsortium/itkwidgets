from imjoy import api
from IPython import get_ipython


class ImJoyViewer:
    """ImJoy Viewer widget class."""
    def __init__(self, **kwargs):
        self.running_in_colab = 'google.colab' in str(get_ipython())
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


def imjoy_view(image=None):
    return api.export(ImJoyViewer(image=image))
