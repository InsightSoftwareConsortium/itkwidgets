"""Interactive visualization of image label statistics.
"""

import numpy as np
import ipywidgets as widgets
from .widget_viewer import Viewer

def label_statistics(image, label_image, histogram=False, bins=64, **viewer_kwargs):
    """Interactive visualization of image label statistics.

    Creates and returns an ipywidget to visualize basic statistics in regions of
    an image's defined by the label image.

    Click or lasso-select labels according to their mean, variance, minimum,
    maximum, or pixel count, and highlight them in the image visualization. The
    intensity histogram is also optionally visualized for the selected labels.

    Parameters
    ----------
    image : array_like, itk.Image, or vtk.vtkImageData
        The 2D or 3D image to compute statistics over and visualize.

    label_image : array_like, itk.Image, or vtk.vtkImageData
        The 2D or 3D label image to visualize.

    histogram : bool
        Compute and display histograms for selected labels.

    bins : int
        Number of bins used for the histograms.

    viewer_kwargs : optional
        Keyword arguments for the viewer. See help(itkwidgets.view).

    """

    if 'ui_collapsed' not in viewer_kwargs:
        viewer_kwargs['ui_collapsed'] = True
    if 'label_image_blend' not in viewer_kwargs:
        viewer_kwargs['label_image_blend'] = 0.75
    viewer = Viewer(image=image, label_image=label_image, **viewer_kwargs)

    try:
        import itk
    except ImportError:
        raise RuntimeError('The itk package is required for the label statistics widget.')
    statistics_filter = itk.LabelStatisticsImageFilter[type(image),
            type(label_image)].New()
    statistics_filter.SetInput(image)
    statistics_filter.SetLabelInput(label_image)
    if histogram:
        statistics_filter.SetUseHistograms(True)
        statistics_filter.SetHistogramParameters(255, float(np.min(image)), float(np.max(image)))
    statistics_filter.Update()

    labels = list(statistics_filter.GetValidLabelValues())
    labels.sort()

    means = []
    variances = []
    minima = []
    maxima = []
    counts = []
    for label in labels:
        minima.append(statistics_filter.GetMinimum(label))
        maxima.append(statistics_filter.GetMaximum(label))
        means.append(statistics_filter.GetMean(label))
        variances.append(statistics_filter.GetVariance(label))
        counts.append(statistics_filter.GetCount(label))

    try:
        import plotly.graph_objs as go
    except ImportError:
        raise RuntimeError('The plotly package is required for the label statistics widget.')
    from plotly.subplots import make_subplots
    fig = make_subplots(rows=1, cols=5)
    fw = go.FigureWidget(fig)

    n_labels = len(labels)
    trace = go.Violin(x=['Mean',]*n_labels, name='Mean', y=means, points='all')
    fw.add_trace(trace, row=1, col=1)
    trace = go.Violin(x=['Variance',]*n_labels, name='Variance', y=variances, points='all')
    fw.add_trace(trace, row=1, col=2)
    trace = go.Violin(x=['Minimum',]*n_labels, name='Minimum', y=minima, points='all')
    fw.add_trace(trace, row=1, col=3)
    trace = go.Violin(x=['Maximum',]*n_labels, name='Maximum', y=maxima, points='all')
    fw.add_trace(trace, row=1, col=4)
    trace = go.Violin(x=['Pixel Count',]*n_labels, name='Count', y=counts, points='all')
    fw.add_trace(trace, row=1, col=5)
    fw.update_layout(showlegend=False, dragmode='lasso')

    off_weight = 0.1
    on_weight = 1.0
    def highlight_selected(trace, points, state):
        if not len(points.point_inds):
            return
        rendered_labels = np.unique(itk.array_view_from_image(viewer.rendered_label_image))
        weights = np.ones((len(rendered_labels),), dtype=np.float32)*off_weight
        # Background
        weights[0] = 0.0
        for index in points.point_inds:
            label = labels[index]
            rendered_index = np.where(rendered_labels == label)[0]
            weights[rendered_index] = on_weight
        viewer.label_image_weights = weights

    for i in range(5):
        fw.data[i].on_click(highlight_selected)
        fw.data[i].on_selection(highlight_selected)

    hist_width = 0
    hist_kwargs = { 'right_sidebar': None }
    if histogram:
        hist_width = 2
        hist_kwargs = {}
    app = widgets.AppLayout(header=viewer,
                            center=widgets.VBox([fw]),
                            left_sidebar=None,
                            pane_widths=[0, 3, hist_width],
                            pane_heights=[3, 2, 0],
                            footer=None,
                            **hist_kwargs)

    if histogram:
        def update_histograms(trace, points, state):
            if not len(points.point_inds):
                return
            hist_fig = go.Figure()
            hist_fw = go.FigureWidget(hist_fig)
            hist_fw.update_layout(xaxis_title='Frequency',
                    yaxis_title='Intensity')
            points.point_inds.sort()
            for index in points.point_inds:
                label = labels[index]
                hist = statistics_filter.GetHistogram(label)
                total = float(hist.GetTotalFrequency())
                min_intensity = hist.GetBinMin(0, 0)
                max_intensity = hist.GetBinMax(0, bins)
                y = np.linspace(min_intensity, max_intensity, bins)
                x = [hist.GetFrequency(i)/total for i in range(hist.GetSize()[0])]
                hist_fw.add_trace(go.Bar(x=x, y=y, name=str(label),
                    orientation='h'))
            hist_fw.update_layout(xaxis_title='Frequency',
                    yaxis_title='Intensity', bargap=0.0)
            app.right_sidebar = widgets.VBox([hist_fw])

        for i in range(5):
            fw.data[i].on_click(update_histograms, append=True)
            fw.data[i].on_selection(update_histograms, append=True)

    return app
