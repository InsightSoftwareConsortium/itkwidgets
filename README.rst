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

These widgets are designed to support image analysis with the `Insight Toolkit
(ITK) <https://itk.org/>`_, but they also work with other spatial analysis tools
in the scientific Python ecosystem.

These widgets are built on
`itk.js <https://github.com/InsightSoftwareConsortium/itk-js>`_ and
`vtk.js <https://github.com/Kitware/vtk-js>`_.

.. image:: https://thumbs.gfycat.com/ShyFelineBeetle-size_restricted.gif
    :width: 640px
    :alt: itk-jupyter-widgets demo
    :align: center

Installation
------------

To install the widgets for the Jupyter Notebook::

  pip install itkwidgets

For Jupyter Lab, additionally run::

  jupyter labextension install @jupyter-widgets/jupyterlab-manager itk-jupyter-widgets

Examples
--------

After installation, try the following examples that demonstrate how to visualize:

- `2D ITK Images <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/2DImage.ipynb>`_
- `3D ITK Images <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/3DImage.ipynb>`_
- `Dask Array images <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/DaskArray.ipynb>`_
- `ImageJ ImgLib2 images <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/ImageJImgLib2.ipynb>`_ (requires `conda <https://conda.io/>`_ and a local `Fiji <https://fiji.sc/>`_ installation)
- `NumPy array images <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/NumPyArray.ipynb>`_ (processed with SciPy)
- `NumPy array images <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/scikit-image.ipynb>`_ (processed with scikit-image)
- `VTK vtkImageData <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/vtkImageData.ipynb>`_

or how to:

- `Select a region of interest <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/SelectRegionOfInterest.ipynb>`_
- `Specify a colormap <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/SpecifyAColormap.ipynb>`_

Examples on Binder
--------

- `2D ITK Images <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itk-jupyter-widgets/master?filepath=examples%2F2DImage.ipynb>`_
- `3D ITK Images <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itk-jupyter-widgets/master?filepath=examples%2F3DImage.ipynb>`_
- `Dask Array images <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itk-jupyter-widgets/master?filepath=examples/DaskArray.ipynb>`_
- `NumPy array images <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itk-jupyter-widgets/master?filepath=examples/NumPyArray.ipynb>`_ (processed with SciPy)
- `NumPy array images <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itk-jupyter-widgets/master?filepath=examples/scikit-image.ipynb>`_ (processed with scikit-image)

- `Select a region of interest <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itk-jupyter-widgets/master?filepath=examples/SelectRegionOfInterest.ipynb>`_
- `Specify a colormap <https://mybinder.org/v2/gh/InsightSoftwareConsortium/itk-jupyter-widgets/master?filepath=examples/SpecifyAColormap.ipynb>`_


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

For a development installation (requires `Node.js <https://nodejs.org/en/download/>`_)::

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
