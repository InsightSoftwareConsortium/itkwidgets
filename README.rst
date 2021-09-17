itkwidgets
==========

.. image:: https://img.shields.io/pypi/v/itkwidgets.svg
    :target: https://pypi.python.org/pypi/itkwidgets
    :alt: PyPI version

.. image:: https://img.shields.io/npm/v/itkwidgets/latest
    :target: https://www.npmjs.com/package/itkwidgets
    :alt: npm

.. image:: https://github.com/InsightSoftwareConsortium/itkwidgets/workflows/Build%20and%20test/badge.svg
    :target: https://github.com/InsightSoftwareConsortium/itkwidgets/actions?query=workflow%3A%22Build+and+test%22
    :alt: Build status

.. image:: https://mybinder.org/badge_logo.svg
    :target: https://mybinder.org/v2/gh/InsightSoftwareConsortium/itkwidgets/master?filepath=examples%2F3DImage.ipynb
    :alt: Interactive example on MyBinder

.. image:: https://img.shields.io/badge/License-Apache%202.0-blue.svg
    :target: https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/LICENSE
    :alt: License

.. image:: https://zenodo.org/badge/121581663.svg
    :target: https://zenodo.org/badge/latestdoi/121581663
    :alt: Software citation DOI

Interactive Jupyter_ widgets to visualize images, point sets, and meshes on the web.

.. image:: https://i.imgur.com/d8aXycW.png
    :width: 800px
    :alt: itkwidgets chest CT in JupyterLab

**Key Features**:

- Visualize 2D and 3D images, point sets, and geometry, e.g. meshes, in Jupyter_
- Support for

  - `NumPy array <https://docs.scipy.org/doc/numpy/reference/generated/numpy.ndarray.html>`_ images
  - `itk.Image <https://itkpythonpackage.readthedocs.io/en/latest/Quick_start_guide.html>`_
  - `Dask array <https://docs.dask.org/en/latest/array.html>`_ images
  - `vtk.vtkImageData <https://vtk.org>`_
  - `pyvista.UniformGrid <https://pyvista.org>`_
  - `vedo.Volume <https://vedo.embl.es/index.html>`_
  - `pyimagej ImageJ / Fiji / ImageJ2 images <https://github.com/imagej/pyimagej>`_
  - Additional NumPy array-like objects
  - `SimpleITK.Image <https://simpleitk-prototype.readthedocs.io/en/latest/user_guide/plot_image.html#sphx-glr-user-guide-plot-image-py>`_

  - NumPy array point sets
  - `itk.PointSet <https://itk.org/Doxygen/html/classitk_1_1PointSet.html>`_
  - `itk.PointBasedSpatialObject <https://itk.org/Doxygen/html/classitk_1_1PointBasedSpatialObject.html>`_
  - `vtk.vtkPolyData <https://vtk.org/doc/nightly/html/classvtkPolyData.html>`_ point sets
  - `pyvista.PolyData <https://docs.pyvista.org/core/points.html>`_ point sets

  - `itk.Mesh <https://itk.org/Doxygen/html/classitk_1_1Mesh.html>`_
  - `itk.PolyLineParametricPath <https://itk.org/Doxygen/html/classitk_1_1PolyLineParametricPath.html>`_
  - `vtk.vtkPolyData <https://vtk.org/doc/nightly/html/classvtkPolyData.html>`_
  - `vtk.vtkStructuredGrid <https://vtk.org/doc/nightly/html/classvtkStructuredGrid.html>`_
  - `vtk.vtkUnstructuredGrid <https://vtk.org/doc/nightly/html/classvtkUnstructuredGrid.html>`_
  - `vtk.vtkActor <https://vtk.org/doc/nightly/html/classvtkActor.html>`_
  - `vtk.vtkVolume <https://vtk.org/doc/nightly/html/classvtkVolume.html>`_
  - `vtk.vtkAssembly <https://vtk.org/doc/nightly/html/classvtkAssembly.html>`_
  - `pyvista.PolyData <https://docs.pyvista.org/core/points.html>`_
  - `pyvista.StructuredGrid <https://docs.pyvista.org/core/point-grids.html#structured-grid-creation>`_
  - `pyvista.UnstructuredGrid <https://docs.pyvista.org/core/point-grids.html#unstructured-grid-creation>`_
  - `vedo.Actor <https://vedo.embl.es/index.html>`_
  - `vedo.Assembly <https://vedo.embl.es/index.html>`_
  - `skan.csr.Skeleton <https://jni.github.io/skan/api/skan.csr.html#module-skan.csr>`_

- Exquisite volume rendering
- Tri-plane volume slicing
- Innovative, powerful opacity transfer function / window / level widget
- Label image segmentation 2D and 3D rendering
- Anisotropic voxel spacing supported
- Image line profile widget
- Image statistics widget
- Compare images widget
- Widgets to select solid colors for geometry or colormaps when point data or
  cell data is available
- Visualize point sets as points or spheres and interactively adjust the point
  size
- Combine with other *ipywidgets* to quickly create graphical interfaces
  that interactively provide insights into data algorithms

.. image:: https://thumbs.gfycat.com/ShyFelineBeetle-size_restricted.gif
    :width: 640px
    :alt: itkwidgets demo
    :align: center

These widgets are designed to support spatial analysis with the `Insight Toolkit
(ITK) <https://itk.org/>`_, but they work equally well with other spatial analysis tools
in the scientific Python ecosystem.

These widgets are built on
`itk.js <https://github.com/InsightSoftwareConsortium/itk-js>`_ and
`vtk.js <https://github.com/Kitware/vtk-js>`_.

Examples on Binder
------------------

Data types:

- `Binder: 2D ITK Images <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itkwidgets/master?filepath=examples%2F2DImage.ipynb>`_
- `Binder: 3D ITK Images <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itkwidgets/master?filepath=examples%2F3DImage.ipynb>`_
- `Binder: 3D Label Images <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itkwidgets/master?filepath=examples%2FLabelImages.ipynb>`_
- `Binder: Dask Array images <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itkwidgets/master?filepath=examples/DaskArray.ipynb>`_
- `Binder: Large volumes <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itkwidgets/master?filepath=examples/LargeVolumes.ipynb>`_
- `Binder: NumPy array images (processed with SciPy) <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itkwidgets/master?filepath=examples/NumPyArrayImage.ipynb>`_
- `Binder: NumPy array images (processed with scikit-image) <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itkwidgets/master?filepath=examples/scikit-image.ipynb>`_
- `Binder: NumPy array for image with anisotropic spacing <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itkwidgets/master?filepath=examples/ImageWithAnisotropicPixelSpacing.ipynb>`_
- `Binder: NumPy array point sets <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itkwidgets/master?filepath=examples/NumPyArrayPointSet.ipynb>`_
- `Binder: ITK Mesh <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itkwidgets/master?filepath=examples/Mesh.ipynb>`_
- `Binder: ITK PointBasedSpatialObject <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itkwidgets/master?filepath=examples/PointBasedSpatialObject.ipynb>`_
- `Binder: skan segmentation skeleton <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itkwidgets/master?filepath=examples/SegmentationSkeleton.ipynb>`_
- `Binder: skan segmentation skeleton <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itkwidgets/master?filepath=examples/SegmentationSkeleton.ipynb>`_

Recipes:

- `Binder: Compare images with a checkerboard pattern <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itkwidgets/master?filepath=examples/Checkerboard.ipynb>`_
- `Binder: Compare images side by side <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itkwidgets/master?filepath=examples/CompareImages.ipynb>`_
- `Binder: Examine a line profile <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itkwidgets/master?filepath=examples/LineProfile.ipynb>`_
- `Binder: Inspect image label statistics <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itkwidgets/master?filepath=examples/ImageLabelStatistics.ipynb>`_
- `Binder: Interactively explore algorithm parameters <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itkwidgets/master?filepath=examples/InteractiveParameterExploration.ipynb>`_
- `Binder: Record a video <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itkwidgets/master?filepath=examples/RecordAVideo.ipynb>`_
- `Binder: Restore a volume opacity transfer function <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itkwidgets/master?filepath=examples/VolumeOpacityTransferFunction.ipynb>`_
- `Binder: Select a region of interest <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itkwidgets/master?filepath=examples/SelectRegionOfInterest.ipynb>`_
- `Binder: Specify camera parameters <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itkwidgets/master?filepath=examples/CameraParameters.ipynb>`_
- `Binder: Specify a colormap <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itkwidgets/master?filepath=examples/SpecifyAColormap.ipynb>`_

Installation
------------

To install the widgets for the Jupyter Notebook with pip::

  pip install itkwidgets

For Jupyter Lab, additionally, run::

  jupyter labextension install @jupyter-widgets/jupyterlab-manager jupyter-matplotlib jupyterlab-datawidgets itkwidgets

.. note::
  JupyterLab 3 support is not yet available. JupyterLab 2 or the Jupyter
  Notebook are possible alternatives.

Usage
-----

In Jupyter, import the ``view`` function::

  from itkwidgets import view

Then, call the ``view`` function at the end of a cell, passing in the image to
examine::

  view(image)

For information on additional options, see the ``view`` function docstring::

  view?

Other available widgets:

- ``itkwidgets.line_profile``: Plot an intensity line profile.
- ``itkwidgets.checkerboard``: Compare two images in a checkerboard pattern.
- ``itkwidgets.compare``: Compare two images side-by-side.

Using within a Docker Container
-------------------------------
You can use ``itkwidgets`` from within a docker container with jupyterlab.
To create a local docker image:

Install ``docker`` and build the docker image with::

  git clone https://github.com/InsightSoftwareConsortium/itkwidgets
  cd itkwidgets/docker
  IMAGE=itkwidgets:0.1.0
  docker build -t $IMAGE .

Then run the docker container with::

  EXAMPLESDIR=`pwd`/../examples
  docker run -it --rm -v $EXAMPLESDIR:/home/jovyan -p 8888:8888 itkwidgets:0.1.0

Finally, connect to your notebook at http://127.0.0.1:8888/lab

Advanced Usage
^^^^^^^^^^^^^^

The *itkwidgets* are based on `ipywidgets
<https://ipywidgets.readthedocs.io/en/latest/examples/Widget%20Basics.html>`_.
As a consequence, widgets traits can be queried, assigned, or observed with
the `viewer` object returned by the `view` function. *itkwidgets* can
be combined with other *ipywidgets* to quickly explore algorithm parameters,
create graphical interfaces, or create data visualization dashboards.

Mouse Controls
^^^^^^^^^^^^^^

**Left click + drag**
  Rotate

**Right click + drag** or **shift + left click + drag**
  Pan

**Mouse wheel** or **control + left click + drag** or **pinch**
  Zoom

**Alt + left click + drag left-right**
  Change color transfer function window

**Shift + left click + drag top-bottom**
  Change color transfer function level

**Shift + alt + left click + drag top-bottom**
  Change primary Gaussian volume opacity transfer function magnitude

Keyboard Shortcuts
^^^^^^^^^^^^^^^^^^

Keyboard shortcuts take effect when the mouse is positioned inside the viewer.
All shortcuts are prefixed with **Alt+**. Corresponding keys for the Dvorak
keyboard layout have the same effect.

**Alt + 1**
  X-plane mode

**Alt + 2**
  Y-plane mode

**Alt + 3**
  Z-plane mode

**Alt + 4**
  Volume rendering mode

**Alt + q**
  Toggle user interface

**Alt + w**
  Toggle region of interest (ROI) selection widget

**Alt + e**
  Reset ROI

**Alt + r**
  Reset camera

**Alt + s**
  Toggle slicing planes in volume rendering mode

**Alt + f**
  Toggle fullscreen


Examples
--------

After installation, try the following examples that demonstrate how to visualize:

- `2D ITK Images <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/2DImage.ipynb>`_
- `3D ITK Images <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/3DImage.ipynb>`_
- `3D Label maps <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/LabelImages.ipynb>`_
- `Dask Array images <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/DaskArray.ipynb>`_
- `Large volumes <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/LargeVolumes.ipynb>`_
- `ImageJ ImgLib2 images <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/ImageJImgLib2.ipynb>`_ (requires `conda <https://conda.io/>`_ and a local `Fiji <https://fiji.sc/>`_ installation)
- `NumPy array images (processed with SciPy) <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/NumPyArrayImage.ipynb>`_
- `NumPy array images (processed with scikit-image) <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/scikit-image.ipynb>`_
- `NumPy array for image with anisotropic spacing <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/ImageWithAnisotropicPixelSpacing.ipynb>`_
- `VTK vtkImageData <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/vtkImageData.ipynb>`_
- `pyvista UniformGrid <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/pyvista.UniformGrid.ipynb>`_
- `NumPy array point sets <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/NumPyArrayPointSet.ipynb>`_
- `ITK Mesh <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/Mesh.ipynb>`_
- `ITK PointBasedSpatialObject <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/PointBasedSpatialObject.ipynb>`_
- `VTK vtkPolyData <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/vtkPolyData.ipynb>`_
- `VTK vtkUnstructuredGrid <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/vtkUnstructuredGrid.ipynb>`_
- `pyvista PolyData <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/pyvista.PolyData.ipynb>`_
- `pyvista StructuredGrid <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/pyvista.StructuredGrid.ipynb>`_
- `pyvista UnstructuredGrid <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/pyvista.UnstructuredGrid.ipynb>`_
- `pyvista LiDAR <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/pyvistaLiDAR.ipynb>`_
- `vedo actors and volumes <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/vedo.ipynb>`_
- `skan segmentation skeleton <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/SegmentationSkeleton.ipynb>`_

or how to:

- `Compares images with a checkerboard pattern <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/Checkerboard.ipynb>`_
- `Compares images side by side <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/CompareImages.ipynb>`_
- `Examine a line profile <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/LineProfile.ipynb>`_
- `Inspect image label statistics <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/ImageLabelStatistics.ipynb>`_
- `Interactively explore algorithm parameters <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/InteractiveParameterExploration.ipynb>`_
- `Record a video <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/RecordAVideo.ipynb>`_
- `Restore a volume opacity transfer function <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/VolumeOpacityTransferFunction.ipynb>`_
- `Select a region of interest <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/SelectRegionOfInterest.ipynb>`_
- `Specify camera parameters <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/CameraParameters.ipynb>`_
- `Specify a colormap <https://github.com/InsightSoftwareConsortium/itkwidgets/blob/master/examples/SpecifyAColormap.ipynb>`_


Troubleshooting
---------------

IOPub data rate exceeded.
^^^^^^^^^^^^^^^^^^^^^^^^^

If you experience the notebook warning::

  IOPub data rate exceeded.
  The notebook server will temporarily stop sending output
  to the client in order to avoid crashing it.
  To change this limit, set the config variable
  `--NotebookApp.iopub_data_rate_limit`.

Set the notebook configuration value::

  jupyter notebook --NotebookApp.iopub_data_rate_limit=1e12


Scrolling in JupyterLab
^^^^^^^^^^^^^^^^^^^^^^^

Cell output scrolls by default in JupyterLab. To disable scrolling, right click
in the region to the left of the output and select *Disable Scrolling for
Outputs*.

'Permission denied' during installation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If *Permission denied* errors occur during installation, install the Python
package with *user* permission via:

  pip install --user itkwidgets

For JupyterLab extension installation, configure JupyterLab to use your user
application directory by setting the environmental variable,
`JUPYTERLAB_DIR`::

  export JUPYTERLAB_DIR=$HOME/.local/share/jupyter/lab

Check that this is picked up in the value of the *Application directory*
reported by::

  jupyter lab path

Then, install the extension as usual::

  jupyter labextension install @jupyter-widgets/jupyterlab-manager jupyter-matplotlib jupyterlab-datawidgets itkwidgets

Hacking
-------

Participation is welcome! For a development installation (requires `Node.js <https://nodejs.org/en/download/>`_)::

  git clone https://github.com/InsightSoftwareConsortium/itkwidgets.git
  cd itkwidgets
  python -m pip install -r requirements-dev.txt -r requirements.txt
  python -m pip install -e .
  jupyter nbextension install --py --symlink --sys-prefix itkwidgets
  jupyter nbextension enable --py --sys-prefix itkwidgets
  jupyter nbextension enable --py --sys-prefix widgetsnbextension
  python -m pytest
  python -m pytest --nbmake examples/*.ipynb

The above commands will setup your system for development with the Jupyter
Notebook. In one terminal, start Jupyter::

  cd itkwidgets
  jupyter notebook

In another terminal, put Webpack in watch mode to rebuild any Javascript
changes when you save a Javascript file::

  cd itkwidgets
  npm run watch

If Python code is changed, restart the kernel to see the changes. If
Javascript code is changed, reload the page after to Webpack has finished
building.

To develop for Jupyter Lab, additionally run::

  jupyter labextension install @jupyter-widgets/jupyterlab-manager jupyter-matplotlib jupyterlab-datawidgets jupyter-webrtc
  jupyter labextension install ./js
  jupyter lab --watch

.. note::

  Historical note: this project was previously named *itk-jupyter-widgets*, but it was renamed to *itkwidgets* to be consistent with the package name.

.. warning::

  This project is under active development. Its API and behavior may change at any time. We mean it.

.. _Jupyter: https://jupyter.org/
