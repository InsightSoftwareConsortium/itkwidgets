from imjoy import api


class ImJoyViewer:
    """ImJoy Viewer widget class."""
    def __init__(self, **kwargs):
        self.image = kwargs.get('image', None)

    async def setup(self):
        viewer = await api.createWindow(
            type='itk-vtk-viewer',
            src='https://kitware.github.io/itk-vtk-viewer/app',
        )
        await viewer.setImage(self.image)


def imjoy_view(image=None):
    return api.export(ImJoyViewer(image=image))
