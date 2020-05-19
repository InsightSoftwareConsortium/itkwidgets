FROM continuumio/miniconda3:4.8.2

RUN adduser --disabled-password --gecos "Default user" --uid 1000 jovyan && \
    apt-get update -y && \
    apt-get install --no-install-recommends -y libgl1-mesa-glx libglu1-mesa && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir /data && chown jovyan:jovyan /data

RUN chown -R 1000 /home/jovyan

COPY environment.yml labextensions.txt /tmp/
RUN conda env update --name base --file /tmp/environment.yml
RUN conda run conda install -y nodejs
RUN conda run jupyter labextension install $(cat /tmp/labextensions.txt)

VOLUME /home/jovyan/
WORKDIR /home/jovyan
EXPOSE 8888
USER root
USER jovyan

CMD bash -l -c "source /opt/conda/bin/activate && jupyter lab --ip=0.0.0.0 --no-browser --NotebookApp.token='' --NotebookApp.allow_origin='*'"
