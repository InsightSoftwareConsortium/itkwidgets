# itkwidgets

[![Documentation Status](https://readthedocs.org/projects/itkwidgets/badge/?version=latest)](https://itkwidgets.readthedocs.io/en/latest/?badge=latest)
[![Notebook tests](https://github.com/InsightSoftwareConsortium/itkwidgets/actions/workflows/notebook-test.yml/badge.svg)](https://github.com/InsightSoftwareConsortium/itkwidgets/actions/workflows/notebook-test.yml)
[![DOI](https://zenodo.org/badge/121581663.svg)](https://zenodo.org/doi/10.5281/zenodo.3603358)


ITKWidgets is an elegant Python interface for visualization on the web platform to interactively generate insights into multidimensional images, point sets, and geometry.

![Hello 3D World](./docs/images/Hello3DWorld.gif)

# Getting Started

## Environment Setup

The [EnvironmentCheck.ipynb](https://github.com/InsightSoftwareConsortium/itkwidgets/blob/main/examples/EnvironmentCheck.ipynb) checks the environment that you are running in to make sure that all required dependencies and extensions are correctly installed. Ideally run first before any other notebooks to prevent common issues around dependencies and extension loading.

## Installation

To install for all environments:

```bash
pip install 'itkwidgets[all]>=1.0a49'
```

### Jupyter Notebook

To install the widgets for the Jupyter Notebook with pip:

```bash
pip install 'itkwidgets[notebook]>=1.0a49'
```

Then look for the ImJoy icon at the top in the Jupyter Notebook:

![ImJoy Icon in Jupyter Notebook](docs/images/imjoy-notebook.png)

### Jupyter Lab

For Jupyter Lab 3 run:

```bash
pip install 'itkwidgets[lab]>=1.0a49'
```

Then look for the ImJoy icon at the top in the Jupyter Notebook:

![ImJoy Icon in Jupyter Lab](docs/images/imjoy-lab.png)

### Google Colab

For Google Colab run:

```bash
pip install 'itkwidgets>=1.0a49'
```

## Example Notebooks

Example Notebooks can be accessed locally by cloning the repository:

```bash
git clone -b main https://github.com/InsightSoftwareConsortium/itkwidgets.git
```

Then navigate into the examples directory:

```bash
cd itkwidgets/examples
```

## Usage

In Jupyter, import the view function:

```python
from itkwidgets import view
```

Then, call the view function at the end of a cell, passing in the image to examine:

```python
view(image)
```

For information on additional options, see the view function docstring:

```python
view?
```

See the [deployments](docs/deployments.md) section for a more detailed overview of additional notebook
options as well as other ways to run and interact with your notebooks.

# Learn more

Visit the [docs](https://itkwidgets.readthedocs.io/en/latest/) for more information on supported notebooks and integrations.
