Quick Start Guide
=================

Installation
------------

To install the widgets for the Jupyter Notebook with pip:

.. code-block::

    pip install itkwidgets imjoy-jupyter-extension

For Jupyter Lab, additionally, run:

.. code-block::

    jupyter labextension install imjoy-jupyter-extension

Then look for the ImJoy icon at the top in the Jupyter Notebook:

.. image:: images/imjoy-notebook.png
    :alt: ImJoy Icon in Jupyter Notebook
    :align: center

Or Jupyter Lab:

.. image:: images/imjoy-lab.png
    :alt: ImJoy Icon in Jupyter Lab
    :align: center

Example Notebooks
-----------------

Example Notebooks can be accessed locally by cloning the repository:

.. code-block::

    git clone -b main https://github.com/InsightSoftwareConsortium/itkwidgets.git

Then navigate into the examples directory:

.. code-block::

    cd <path-to-itkwidgets>/examples

Usage
-----

In Jupyter, import the view function:

.. code-block::

    from itkwidgets import view

Then, call the view function at the end of a cell, passing in the image to examine:

.. code-block::

    view(image)

For information on additional options, see the view function docstring:

.. code-block::

    view?

See the :doc:`deployments` section for a more detailed overview of additional notebook
options as well as other ways to run and interact with your notebooks.
