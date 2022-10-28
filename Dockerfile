# Use Alpine Python 3 Image as Base
FROM python:3-alpine

# Set Environment Variables
ENV PUID=1000
ENV PGID=1000
ENV USER=abc

# Add Non-Root User
RUN set -eux; \
  echo "**** create $USER user and $USER group with home directory /opt/sigma ****" && \
  addgroup -S $USER && \
  adduser -u $PUID -s /bin/false -h /opt/sigma -S -G $USER $USER && \
  adduser $USER users

# Add Files
COPY sigma/cli /opt/sigma/

# Change Directory
WORKDIR /opt/sigma-cli

# Install Python Modules
RUN set -eux; \
  python -m pip install sigma-cli; \
  chmod -R abc. /opt/sigma;

# Use sigma as entrypoint
ENTRYPOINT ["sigma"]

