Integrations
============

NumPy
-----

Install NumPy:

.. code::

    pip install numpy

Or see the `NumPy docs`_ for advanced installation options.

.. _NumPy docs: https://numpy.org/install/

Use NumPy to build and view your data:

.. code:: 

    import numpy as np
    from itkwidgets import view

    number_of_points = 3000
    gaussian_mean = [0.0, 0.0, 0.0]
    gaussian_cov = [[1.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 0.5]]
    point_set = np.random.multivariate_normal(gaussian_mean, gaussian_cov, number_of_points)

    view(point_sets=point_set)

Or check out the `NumPyArrayPointSet`_ example notebook to try it out for
yourself!

.. _NumPyArrayPointSet: https://colab.research.google.com/github/InsightSoftwareConsortium/itkwidgets/blob/main/examples/NumPyArrayPointSet.ipynb

.. image:: images/numpy.png
    :alt: NumPy Array Point Set
    :align: center

ITK
---

Install ITK:

.. code:: 

    pip install --pre itk-io

You can use ITK to read in and filter your data before displaying and
interacting with it with the Viewer.

.. code:: 

    import os
    import itk
    from itkwidgets import view
    from urllib.request import urlretrieve

    # Download data
    file_name = '005_32months_T2_RegT1_Reg2Atlas_ManualBrainMask_Stripped.nrrd'
    if not os.path.exists(file_name):
        url = 'https://data.kitware.com/api/v1/file/564a5b078d777f7522dbfaa6/download'
        urlretrieve(url, file_name)

    image = itk.imread(file_name)
    view(image, rotate=True, gradient_opacity=0.4)

Get started with ITK in the `3DImage`_ notebook. You can also visit the
`ITK docs`_ for additional examples for getting started.

.. _3DImage: https://colab.research.google.com/github/InsightSoftwareConsortium/itkwidgets/blob/main/examples/integrations/itk/3DImage.ipynb
.. _ITK docs: https://itkpythonpackage.readthedocs.io/en/latest/Quick_start_guide.html#usage

.. image:: images/itkimage.png
    :alt: ITK 3D Image
    :align: center

VTK
---

Install VTK:

.. code:: 

    pip install vtk

You can build you own VTK data or read in a file to pass to the Viewer.

.. code:: 

    import os
    import vtk
    from itkwidgets import view
    from urllib.request import urlretrieve

    # Download data
    file_name = 'vase.vti'
    if not os.path.exists(file_name):
        url = 'https://data.kitware.com/api/v1/file/5a826bdc8d777f0685782960/download'
        urlretrieve(url, file_name)

    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(file_name)
    reader.Update()
    vtk_image = reader.GetOutput()

    viewer = view(vtk_image)

Please be sure to check out the extensive list of `Python VTK examples`_ that
are available for the majority of the available VTK classes, or jump right in
with the `vtkImageData`_ or `vtkPolyDataPointSet`_ example notebooks.

.. _Python VTK Examples: https://kitware.github.io/vtk-examples/site/Python/
.. _vtkImageData: https://colab.research.google.com/github/InsightSoftwareConsortium/itkwidgets/blob/main/examples/integrations/vtk/vtkImageData.ipynb
.. _vtkPolyDataPointSet: https://colab.research.google.com/github/InsightSoftwareConsortium/itkwidgets/blob/main/examples/integrations/vtk/vtkPolyDataPointSet.ipynb

.. image:: images/vtkpolydata.png
    :alt: vtkPolyData as a Point Set
    :align: center

MONAI
-----

MONAI is a PyTorch-based, open-source framework for deep learning in healthcare
imaging. Get started by installing MONAI:

.. code:: 

    pip install monai

By default only the minimal requirements are installed. The extras syntax can
be used to install optional dependencies. For example,

.. code:: 

    pip install 'monai[nibabel, skimage]'

For a full list of available options visit the `MONAI docs`_.

.. _MONAI docs: https://docs.monai.io/en/stable/installation.html#installing-the-recommended-dependencies

Check out the `transform_visualization`_ notebook for an example of visualize
PyTorch tensors.

.. _transform_visualization: https://colab.research.google.com/github/InsightSoftwareConsortium/itkwidgets/blob/main/examples/integrations/MONAI/transform_visualization.ipynb

.. image:: images/monai_pytorch.png
    :alt: MONAI transformed tensor
    :align: center

dask
----

Dask offers options for installation so that you include only as much or little
as you need:

.. code:: 

    pip install "dask[complete]"    # Install everything
    pip install dask                # Install only core parts of dask
    pip install "dask[array]"       # Install requirements for dask array
    pip install "dask[dataframe]"   # Install requirements for dask dataframe

See the `full documentation`_ for additional dependency sets and installation
options.

.. _full documentation: https://docs.dask.org/en/stable/install.html#dask-installation

You can read in and visualize a dask array in just a few lines of code:

.. code:: 

    import os
    import zipfile
    import dask.array.image
    from itkwidgets import view
    from urllib.request import urlretrieve

    # Download data
    file_name = 'emdata_janelia_822252.zip'
    if not os.path.exists(file_name):
        url = 'https://data.kitware.com/api/v1/file/5bf232498d777f2179b18acc/download'
        urlretrieve(url, file_name)
    with zipfile.ZipFile(file_name, 'r') as zip_ref:
        zip_ref.extractall()

    stack = dask.array.image.imread('emdata_janelia_822252/*')

    view(stack, shadow=False, gradient_opacity=0.4, ui_collapsed=True)

Try it yourself in the `DaskArray`_ notebook.

.. _DaskArray: https://colab.research.google.com/github/InsightSoftwareConsortium/itkwidgets/blob/main/examples/integrations/dask/DaskArray.ipynb

.. image:: images/dask_stack.png
    :alt: Dask stack
    :align: center
.. image:: images/dask.png
    :alt: Dask data
    :align: center

xarray
------

Xarray uses labels (dimensions, coordinates and attributes) on top of raw data
to provide a powerful, concise interface with operations like

.. code:: 

    x.sum('time')

Xarray has a few required dependencies that must be installed as well:

.. code:: 

    pip install numpy     # 1.18 or later
    pip install packaging # 20.0 or later
    pip install pandas    # 1.1 or later
    pip install xarray

Build your own xarray DataArray or Dataset or check out `xarray-data`_ for sample
data to visualize.

.. _xarray-data: https://github.com/pydata/xarray-data

.. code:: 

    import numpy as np
    import xarray as xr
    from itkwidgets import view

    ds = xr.tutorial.open_dataset("ROMS_example.nc", chunks={"ocean_time": 1})

    view(ds.zeta, ui_collapsed=False, cmap="Asymmtrical Earth Tones (6_21b)", sample_distance=0)

.. image:: images/xarray.png
    :alt: xarray ROMS example data
    :align: center

The `DataArray`_ notebook provides an example using the ROMS_example provided
by xarray-data.

.. _DataArray: https://colab.research.google.com/github/InsightSoftwareConsortium/itkwidgets/blob/main/examples/integrations/xarray/DataArray.ipynb

.. image:: images/xarray2.png
    :alt: xarray ROMS example data
    :align: center

PyVista
-------
PyVista is Pythonic VTK, providing mesh data structures and filtering methods
for spatial datasets and is easy to install and get started with:

.. code:: 

    pip install pyvista

The `Core API`_ provides an overview of the supported data types and the
`examples`_ module provides a nice selection of sample data that you can use
to get started.

.. _Core API: https://docs.pyvista.org/api/core/index.html
.. _examples: https://docs.pyvista.org/api/examples/_autosummary/pyvista.examples.examples.html#module-pyvista.examples.examples

The `UniformGrid`_ and `LiDAR`_ notebooks demonstrate PyVista data being
visualized with the Viewer.

.. _UniformGrid: https://colab.research.google.com/github/InsightSoftwareConsortium/itkwidgets/blob/main/examples/integrations/PyVista/UniformGrid.ipynb
.. _LiDAR: https://colab.research.google.com/github/InsightSoftwareConsortium/itkwidgets/blob/main/examples/integrations/PyVista/LiDAR.ipynb

.. image:: images/pyvista.png
    :alt: PyVista LiDAR point set
    :align: center

PyImageJ
--------

PyImageJ provides a set of wrapper functions for integration between ImageJ2
and Python and the simplest way to install PyImageJ is with Conda because if
you use pip you will need to manage the OpenJDK and Maven dependencies
separately. See the `Conda docs`_ for installation on your system or follow
PyImageJ's suggestion of using Mamba (`install Mambaforge`_).

.. _Conda docs: https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html
.. _install Mambaforge: https://github.com/conda-forge/miniforge#mambaforge

.. code:: 

    mamba create -n pyimagej pyimagej openjdk=8

For more detatiled installation instructions and alternativate options like pip,
see the `PyImageJ installation docs`_.

.. _PyImageJ Installation docs: https://github.com/imagej/pyimagej/blob/master/doc/Install.md

Run the ImageJImgLib2 notebook to see how we can load images and apply filters
before viewing them in the Viewer.

.. image:: images/pyimagej.png
    :alt: PyImageJ Filtered blood vessels image
    :align: center

Zarr
----

Zarr is a format for the storage of chunked, compressed, N-dimensional arrays
that supports chunking arrays along any dimension, reading or writing arrays
concurrently from multiple threads or processes, as well as organizing arrays
into hierarchies via groups.

To install Zarr:

.. code:: 

    pip install zarr

You can use Zarr to read data stored locally or on S3, as we do in the
`OME-NGFF-Brainstem-MRI`_ example notebook.

.. _OME-NGFF-Brainstem-MRI: https://colab.research.google.com/github/InsightSoftwareConsortium/itkwidgets/blob/main/examples/integrations/zarr/OME-NGFF-Brainstem-MRI.ipynb

.. code:: 

    from zarr.storage import FSStore

    fsstore = FSStore('https://dandiarchive.s3.amazonaws.com/zarr/7723d02f-1f71-4553-a7b0-47bda1ae8b42')
    brainstem = zarr.open_group(fsstore, mode='r')

    view(brainstem)

.. image:: images/zarr.png
    :alt: Brainstem image from zarr
    :align: center
