"""Checkerboard class

Compare two images with a checkerboard pattern. This is particularly useful for
examining registration results.
"""

import ipywidgets as widgets
from .widget_viewer import Viewer
import itk
from ._to_itk import to_itk_image

def checkerboard(image1, image2, pattern=3, **viewer_kwargs):
    """Compare two images with a checkerboard pattern.

    This is particularly useful for examining registration results.

    Parameters
    ----------
    image1 : array_like, itk.Image, or vtk.vtkImageData
        First image to use in the checkerboard.

    image2 : array_like, itk.Image, or vtk.vtkImageData
        Second image to use in the checkerboard.

    pattern : int, optional, default: 3
        Size of the checkerboard pattern.

    viewer_kwargs : optional
        Keyword arguments for the viewer. See help(itkwidgets.view).

    """

    itk_image1 = to_itk_image(image1)
    if not itk_image1:
        itk_image1 = itk.output(image1)
    itk_image2 = to_itk_image(image2)
    if not itk_image2:
        itk_image2 = itk.output(image2)

    checkerboard_filter = itk.CheckerBoardImageFilter.New(itk_image1, itk_image2)

    dimension = image1.GetImageDimension()
    checker_pattern = [pattern]*dimension
    checkerboard_filter.SetCheckerPattern(checker_pattern)

    checkerboard_filter.Update()
    checkerboard = checkerboard_filter.GetOutput()

    if 'annotations' not in viewer_kwargs:
        viewer_kwargs['annotations'] = False
    if 'interpolation' not in viewer_kwargs:
        viewer_kwargs['interpolation'] = False
    if 'ui_collapsed' not in viewer_kwargs:
        viewer_kwargs['ui_collapsed'] = True
    viewer = Viewer(image=checkerboard, **viewer_kwargs)

    max_size1 = int(min(itk.size(image1)) / 8)
    max_size1 = max(max_size1, pattern*2)
    max_size2 = int(min(itk.size(image2)) / 8)
    max_size2 = max(max_size2, pattern*2)
    max_size = max(max_size1, max_size2)

    pattern_slider = widgets.IntSlider(value=pattern, min=2, max=max_size,
            step=1, description='Pattern size:')
    def update_checkerboard(change):
        checker_pattern = [change.new]*dimension
        checkerboard_filter.SetCheckerPattern(checker_pattern)
        checkerboard_filter.Update()
        viewer.image = checkerboard_filter.GetOutput()
    pattern_slider.observe(update_checkerboard, ['value'])

    widget = widgets.VBox([viewer, pattern_slider])

    return widget
