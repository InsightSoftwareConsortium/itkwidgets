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
    :target: https://mybinder.org/v2/gh/4QuantOSS/itk-jupyter-widgets/master

Interactive `Jupyter <https://jupyter.org/>`_ widgets to visualize images in 2D and 3D.

.. image:: https://i.imgur.com/ERK5JtT.png
    :width: 800px
    :alt: Monkey brain volume rendering

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

To install, use pip::

  pip install itkwidgets
  jupyter nbextension install --py --sys-prefix itkwidgets
  jupyter nbextension enable --py --sys-prefix itkwidgets

Examples
--------

After installation, try the following examples that demonstrate how to visualize:

- `2D ITK Images <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/2DImage.ipynb>`_
- `3D ITK Images <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/3DImage.ipynb>`_
- `ImageJ ImgLib2 images <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/ImageJImgLib2.ipynb>`_ (requires `conda <https://conda.io/>`_ and a local `Fiji <https://fiji.sc/>`_ installation)
- `NumPy array images <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/NumPyArray.ipynb>`_ (processed with SciPy)
- `VTK vtkImageData <https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/examples/vtkImageData.ipynb>`_

Examples on Binder
--------

-  `3D ITK Images <https://mybinder.org/v2/gh/4QuantOSS/itk-jupyter-widgets/master?filepath=examples%2F3DImage.ipynb>`_

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

.. warning::

  This project is under active development. Its API and behavior may change at
  any time. We mean it.
