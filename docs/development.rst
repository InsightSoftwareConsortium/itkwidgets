Development
===========

Note: `Node.js`_ is required for development.

.. _Node.js: https://nodejs.org/en/download/

Setup your system for development:

.. code-block::

    git clone https://github.com/InsightSoftwareConsortium/itkwidgets.git
    cd itkwidgets
    python -m pip install -r requirements-dev.txt
    python -m pip install -e .
    python -m pytest
    python -m pytest --nbmake examples/*.ipynb

If Python code is changed, restart the kernel to see the changes.

**Warning**: This project is under active development. Its API and behavior may change at any time. We mean it.
