# Quick Start Guide

## Environment Setup

The [EnvironmentCheck.ipynb](https://github.com/InsightSoftwareConsortium/itkwidgets/blob/main/examples/EnvironmentCheck.ipynb) checks the environment that you are running in to make sure that all required dependencies and extensions are correctly installed. Ideally run first before any other notebooks to prevent common issues around dependencies and extension loading.

## Installation

To install for all environments:

```bash
pip install 'itkwidgets[all]>=1.0a23'
```

### Jupyter Notebook

To install the widgets for the Jupyter Notebook with pip:

```bash
pip install 'itkwidgets[notebook]>=1.0a23'
```

Then look for the ImJoy icon at the top in the Jupyter Notebook:

![ImJoy Icon in Jupyter Notebook](images/imjoy-notebook.png)

### Jupyter Lab

For Jupyter Lab 3 run:

```bash
pip install 'itkwidgets[lab]>=1.0a23'
```

Then look for the ImJoy icon at the top in the Jupyter Notebook:

![ImJoy Icon in Jupyter Lab](images/imjoy-lab.png)

### Google Colab

For Google Colab run:

```bash
pip install 'itkwidgets>=1.0a23'
```

### Command Line (CLI)

```bash
pip install 'itkwidgets[cli]>=1.0a35'
playwright install --with-deps chromium
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

### Notebook

In Jupyter, import the {py:obj}`view <itkwidgets.viewer.view>` function:

```python
from itkwidgets import view
```

Then, call the {py:obj}`view <itkwidgets.viewer.view>` function at the end of a cell, passing in the image to examine:

```python
view(image)
```

For information on additional options, see the {py:obj}`view <itkwidgets.viewer.view>` function docstring:

```python
view?
```

### CLI

```bash
itkwidgets path/to/image -b # open viewer in browser -OR-

itkwidgets path/to/image    # display preview in terminal
```

For information on additional options, see the help:

```bash
itkwidgets --help
```

See the [deployments](deployments.md) section for a more detailed overview of additional options as well as other ways to run and interact with the itkwidgets.
