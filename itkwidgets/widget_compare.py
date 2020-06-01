import numpy as np
import ipywidgets as widgets
from itkwidgets.widget_viewer import Viewer
from traitlets import CBool
import IPython

def compare(image1, image2,
            link_cmap=False, link_gradient_opacity=False,
            **viewer_kwargs):
    """Compare two images by visualizing them side by side.

    Visualization traits, e.g. the view mode, camera, etc., are linked
    between the viewers. Optional trait linking can be enabled in widget's
    user interface.
    """

    viewer1 = Viewer(image=image1, **viewer_kwargs)
    # Collapse the second viewer's user interface by default.
    if 'ui_collapsed' not in viewer_kwargs:
            viewer_kwargs['ui_collapsed'] = True
    viewer2 = Viewer(image=image2, **viewer_kwargs)


    widgets.jslink((viewer1, 'mode'), (viewer2, 'mode'))
    widgets.jslink((viewer1, 'camera'), (viewer2, 'camera'))
    widgets.jslink((viewer1, 'roi'), (viewer2, 'roi'))
    widgets.jslink((viewer1, 'rotate'), (viewer2, 'rotate'))
    widgets.jslink((viewer1, 'annotations'), (viewer2, 'annotations'))
    widgets.jslink((viewer1, 'x_slice'), (viewer2, 'x_slice'))
    widgets.jslink((viewer1, 'y_slice'), (viewer2, 'y_slice'))
    widgets.jslink((viewer1, 'z_slice'), (viewer2, 'z_slice'))
    widgets.jslink((viewer1, 'slicing_planes'), (viewer2, 'slicing_planes'))

    link_widgets = []
    link_widgets.append(widgets.Label('Link:'))

    class UpdateLink(object):
        def __init__(self, enable, name):
            self.link = None
            self.name = name
            if enable:
                self.link = widgets.jslink((viewer1, name), (viewer2, name))

        def __call__(self, change):
            if change.new:
                self.link = widgets.jslink((viewer1, self.name), (viewer2, self.name))
            else:
                self.link.unlink()

    link_cmap_widget = widgets.Checkbox(description='cmap', value=link_cmap)
    update_cmap_link = UpdateLink(link_cmap, 'cmap')
    link_cmap_widget.observe(update_cmap_link, 'value')
    link_widgets.append(link_cmap_widget)

    link_gradient_opacity_widget = widgets.Checkbox(description='gradient_opacity', value=link_gradient_opacity)
    update_gradient_opacity_link = UpdateLink(link_gradient_opacity, 'gradient_opacity')
    link_gradient_opacity_widget.observe(update_gradient_opacity_link, 'value')
    link_widgets.append(link_gradient_opacity_widget)

    link_widget = widgets.HBox(link_widgets)

    widget = widgets.AppLayout(header=None,
            left_sidebar=viewer1,
            center=None,
            right_sidebar=viewer2,
            footer=link_widget,
            pane_heights=[1, 6, 1])
    return widget
