itk-jupyter-widgets
===============================

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets/blob/master/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/itkwidgets.svg)](https://pypi.python.org/pypi/itkwidgets)
[![Build Status](https://circleci.com/gh/InsightSoftwareConsortium/itk-jupyter-widgets.svg?style=shield)](https://circleci.com/gh/InsightSoftwareConsortium/itk-jupyter-widgets)

Interactive [Jupyter](https://jupyter.org/) widgets to visualize images in 2D and 3D.

<img src="https://i.imgur.com/ERK5JtT.png" width="800" alt="Monkey brain volume rendering">

These widgets are designed to support image analysis with the [Insight Toolkit
(ITK)](https://itk.org/), but they also work with other spatial analysis tools
in the scientific Python ecosystem.

These widgets are built on
[itk.js](https://github.com/InsightSoftwareConsortium/itk-js) and
[vtk.js](https://github.com/Kitware/vtk-js).

Installation
------------

To install, use pip:

```sh
pip install itkwidgets
jupyter nbextension enable --py --sys-prefix itkwidgets
```


For a development installation (requires [Node.js](https://nodejs.org/en/download/)),

```sh
git clone https://github.com/InsightSoftwareConsortium/itk-jupyter-widgets.git
cd itk-jupyter-widgets
python -m pip install -r requirements-dev.txt -r requirements.txt
python -m pip install -e .
jupyter nbextension install --py --symlink --sys-prefix itkwidgets
jupyter nbextension enable --py --sys-prefix itkwidgets
jupyter nbextension enable --py --sys-prefix widgetsnbextension
python -m pytest
```
