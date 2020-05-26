FROM jupyter/base-notebook:python-3.7.6
# jupyter/base-notebook:python-3.7.6 includes:
# - 'notebook=6.0.3'
# - 'jupyterhub=1.1.0'
# - 'jupyterlab=2.1.1'

LABEL maintainer="InsightSoftwareConsortium"

USER root
RUN apt-get update \
 && apt-get install  -yq --no-install-recommends \
    libgl1-mesa-glx \
    libglu1-mesa \
    libsm6 \
 && apt-get clean && rm -rf /var/lib/apt/lists/*
USER jovyan

# setup the itkwidgets conda enviornment
COPY environment.yml labextensions.txt /tmp/
RUN conda env update --name base --file /tmp/environment.yml
RUN conda run conda install -y nodejs
RUN conda run jupyter labextension install $(cat /tmp/labextensions.txt)