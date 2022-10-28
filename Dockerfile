# Use Alpine Python 3 Image as Base
FROM python:3-alpine

# Add Files
COPY sigma-cli /opt/
# Change Directory
WORKDIR /opt/sigma-cli

# Install Python Modules
RUN set -eux; \
  python -m pipx install sigma-cli;

# Use sigma as entrypoint
ENTRYPOINT ["sigma"]

