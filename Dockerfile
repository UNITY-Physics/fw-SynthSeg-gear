# Use the latest Python 3 docker image
# FROM nialljb/fw-synthseg:0.2.0 as base
FROM nialljb/freesurfer-centos9:0.0.1

ENV HOME=/root/
ENV FLYWHEEL="/flywheel/v0"
WORKDIR $FLYWHEEL
RUN mkdir -p $FLYWHEEL/input

# Installing the current project (most likely to change, above layer can be cached)
COPY ./ $FLYWHEEL/
COPY license.txt /usr/local/freesurfer/.license
COPY fslinstaller.py $FLYWHEEL/

RUN dnf update -y && \
    dnf install -y unzip gzip wget && \
    dnf install epel-release -y && \
    dnf install ImageMagick -y && \
    dnf clean all

RUN pip3 install flywheel-gear-toolkit && \
    pip3 install flywheel-sdk==19.3.0 && \
    pip3 install jsonschema && \
    pip3 install pandas 

# Configure entrypoint
RUN bash -c 'chmod +rx $FLYWHEEL/run.py' && \
    bash -c 'chmod +rx $FLYWHEEL/app/' && \
    bash -c 'chmod +rx $FLYWHEEL/utils/render.sh' 
ENTRYPOINT ["python3","/flywheel/v0/start.sh"] 
# Flywheel reads the config command over this entrypoint