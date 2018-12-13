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
    input1 = itk_image1
    input2 = itk_image2

    region_image1 = itk_image1.GetLargestPossibleRegion()
    region_image2 = itk_image2.GetLargestPossibleRegion()
    same_physical_space = \
        np.allclose(np.array(itk_image1.GetOrigin()), np.array(itk_image2.GetOrigin())) and \
        np.allclose(np.array(itk_image1.GetSpacing()), np.array(itk_image2.GetSpacing())) and \
        itk_image1.GetDirection() == itk_image2.GetDirection() and \
        np.allclose(np.array(region_image1.GetIndex()), np.array(region_image2.GetIndex())) and \
        np.allclose(np.array(region_image1.GetSize()), np.array(region_image2.GetSize()))
    if not same_physical_space:
        upsample_image2 = True
        if itk_image1.GetSpacing() != itk_image2.GetSpacing():
            min1 = min(itk_image1.GetSpacing())
            min2 = min(itk_image2.GetSpacing())
            if min2 < min1:
                upsample_image2 = False
        else:
            size1 = max(itk.size(itk_image1))
            size2 = max(itk.size(itk_image1))
            if size2 > size1:
                upsample_image2 = False

        if upsample_image2:
            resampler = itk.ResampleImageFilter.New(itk_image2)
            resampler.UseReferenceImageOn()
            resampler.SetReferenceImage(itk_image1)
            resampler.Update()
            input2 = resampler.GetOutput()
        else:
            resampler = itk.ResampleImageFilter.New(itk_image1)
            resampler.UseReferenceImageOn()
            resampler.SetReferenceImage(itk_image2)
            resampler.Update()
            input1 = resampler.GetOutput()

    checkerboard_filter = itk.CheckerBoardImageFilter.New(input1, input2)

    dimension = itk_image1.GetImageDimension()
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

    # Heuristic to specify the max pattern size
    max_size1 = int(min(itk.size(itk_image1)) / 8)
    max_size1 = max(max_size1, pattern*2)
    max_size2 = int(min(itk.size(itk_image2)) / 8)
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
