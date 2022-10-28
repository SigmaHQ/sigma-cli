# Use Alpine Python 3 Image as Base
FROM python:3-alpine

# Set Environment Variables
ENV PUID=1000
ENV PGID=1000

# Add Non-Root User
RUN set -eux; \
  echo "**** create abc user and make our folders ****" && \
  groupmod -g $PGID users && \
  useradd -u $PUID -U -d /config -s /bin/false abc && \
  usermod -G users abc && \
  mkdir -p /opt/sigma && \
  chmod -R abc. /opt/sigma
  
  
# Add Files
COPY sigma/cli /opt/sigma/

# Change Directory
WORKDIR /opt/sigma-cli

# Install Python Modules
RUN set -eux; \
  python -m pipx install sigma-cli; \
  chmod -R abc. /opt/sigma;

# Use sigma as entrypoint
ENTRYPOINT ["sigma"]

