itk-jupyter-widgets
===============================

Interactive [Jupyter](https://jupyter.org/) widgets to visualize images in 2D and 3D.

These widgets are designed to support image analysis with the [Insight Toolkit
(ITK)](https://itk.org/), but they also work with other spatial analysis tools
in the scientific Python ecosystem.

These widgets art built on
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
