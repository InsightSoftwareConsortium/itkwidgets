itk-jupyter-widgets
===================

.. image:: https://img.shields.io/badge/License-Apache%202.0-blue.svg
    :target: https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/LICENSE
    :alt: License

.. image:: https://img.shields.io/pypi/v/itkwidgets.svg
    :target: https://pypi.python.org/pypi/itkwidgets
    :alt: PyPI

.. image:: https://circleci.com/gh/InsightSoftwareConsortium/itk-jupyter-widgets.svg?style=shield
    :target: https://circleci.com/gh/InsightSoftwareConsortium/itk-jupyter-widgets
    :alt: Build status

.. image:: https://mybinder.org/badge.svg
    :target: https://mybinder.org/v2/gh/InsightSoftwareConsortium/itk-jupyter-widgets/master?filepath=examples%2F3DImage.ipynb

Interactive `Jupyter <https://jupyter.org/>`_ widgets to visualize images in 2D and 3D.

.. image:: https://i.imgur.com/d8aXycW.png
    :width: 800px
    :alt: itk-jupyter-widgets chest CT in JupyterLab

**Key Features**:

- Exquisite volume rendering
- Tri-plane volume slicing
- Innovative, powerful opacity transfer function / window / level widget
- Support for

  - NumPy Arrays
  - itk.Image
  - vtk.vtkImageData, pyvista.UniformGrid
  - Dask Arrays
  - ImageJ / Fiji / ImageJ2 images
  - Additional NumPy Array-like objects

- Anisotropic voxel spacing supported
- 3D and 2D image support
- Line profiles
- Combine with other *ipywidgets* to quickly create graphical interfaces to
  algorithms

.. image:: https://thumbs.gfycat.com/ShyFelineBeetle-size_restricted.gif
    :width: 640px
    :alt: itk-jupyter-widgets demo
    :align: center

These widgets are designed to support image analysis with the `Insight Toolkit
(ITK) <https://itk.org/>`_, but they also work with other spatial analysis tools
in the scientific Python ecosystem.

These widgets are built on
`itk.js <https://github.com/InsightSoftwareConsortium/itk-js>`_ and
`vtk.js <https://github.com/Kitware/vtk-js>`_.

Examples on Binder
------------------

Data types:

- `Binder: 2D ITK Images <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itk-jupyter-widgets/master?filepath=examples%2F2DImage.ipynb>`_
- `Binder: 3D ITK Images <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itk-jupyter-widgets/master?filepath=examples%2F3DImage.ipynb>`_
- `Binder: Dask Array images <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itk-jupyter-widgets/master?filepath=examples/DaskArray.ipynb>`_
- `Binder: Large volumes <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itk-jupyter-widgets/master?filepath=examples/LargeVolumes.ipynb>`_
- `Binder: NumPy array images (processed with SciPy) <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itk-jupyter-widgets/master?filepath=examples/NumPyArray.ipynb>`_
- `Binder: NumPy array images  (processed with scikit-image) <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itk-jupyter-widgets/master?filepath=examples/scikit-image.ipynb>`_

Tasks:

- `Binder: Compare images with a checkerboard pattern <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itk-jupyter-widgets/master?filepath=examples/Checkerboard.ipynb>`_
- `Binder: Examine a line profile <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itk-jupyter-widgets/master?filepath=examples/LineProfile.ipynb>`_
- `Binder: Interactively explore algorithm parameters <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itk-jupyter-widgets/master?filepath=examples/InteractiveParameterExploration.ipynb>`_
- `Binder: Record a video <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itk-jupyter-widgets/master?filepath=examples/RecordAVideo.ipynb>`_
- `Binder: Select a region of interest <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itk-jupyter-widgets/master?filepath=examples/SelectRegionOfInterest.ipynb>`_
- `Binder: Specify a colormap <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itk-jupyter-widgets/master?filepath=examples/SpecifyAColormap.ipynb>`_

Installation
------------

To install the widgets for the Jupyter Notebook with pip::

  pip install itkwidgets

or with conda::

  conda install -c conda-forge itkwidgets

For Jupyter Lab, additionally run::

  jupyter labextension install @jupyter-widgets/jupyterlab-manager itk-jupyter-widgets

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

Advanced Usage
^^^^^^^^^^^^^^

The *itk-jupyter-widgets* are based on `ipywidgets
<https://ipywidgets.readthedocs.io/en/latest/examples/Widget%20Basics.html>`_.
As a consequence, widgets traits can be queried, assigned, or observed with
the `viewer` object returned by the `view` function. *itk-jupyter-widgets* can
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

- `2D ITK Images <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/2DImage.ipynb>`_
- `3D ITK Images <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/3DImage.ipynb>`_
- `Dask Array images <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/DaskArray.ipynb>`_
- `Large volumes <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/LargeVolumes.ipynb>`_
- `ImageJ ImgLib2 images <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/ImageJImgLib2.ipynb>`_ (requires `conda <https://conda.io/>`_ and a local `Fiji <https://fiji.sc/>`_ installation)
- `NumPy array images (processed with SciPy) <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/NumPyArray.ipynb>`_
- `NumPy array images (processed with scikit-image) <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/scikit-image.ipynb>`_
- `VTK vtkImageData <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/vtkImageData.ipynb>`_
- `pyvista UniformGrid <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/pyvista.UniformGrid.ipynb>`_

or how to:

- `Compares images with a checkerboard pattern <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/Checkerboard.ipynb>`_
- `Examine a line profile <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/LineProfile.ipynb>`_
- `Interatively explore algorithm parameters <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/InteractiveParameterExploration.ipynb>`_
- `Record a video <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/RecordAVideo.ipynb>`_
- `Select a region of interest <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/SelectRegionOfInterest.ipynb>`_
- `Specify a colormap <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/SpecifyAColormap.ipynb>`_


Troubleshooting
---------------

If you experience the notebook warning::

  IOPub data rate exceeded.
  The notebook server will temporarily stop sending output
  to the client in order to avoid crashing it.
  To change this limit, set the config variable
  `--NotebookApp.iopub_data_rate_limit`.

Set the notebook configuration value::

  jupyter notebook --NotebookApp.iopub_data_rate_limit=1e12

Hacking
-------

Participation is welcome! For a development installation (requires `Node.js <https://nodejs.org/en/download/>`_)::

  git clone https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets.git
  cd itk-jupyter-widgets
  python -m pip install -r requirements-dev.txt -r requirements.txt
  python -m pip install -e .
  jupyter nbextension install --py --symlink --sys-prefix itkwidgets
  jupyter nbextension enable --py --sys-prefix itkwidgets
  jupyter nbextension enable --py --sys-prefix widgetsnbextension
  python -m pytest

The above commands will setup your system for development with the Jupyter
Notebook. To develop for Jupyter Lab, additionally run::

  jupyter labextension install @jupyter-widgets/jupyterlab-manager
  jupyter labextension install ./js

.. warning::

  This project is under active development. Its API and behavior may change at
  any time. We mean it.
