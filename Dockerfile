# Use Alpine Python 3 Image as Base
FROM python:3-alpine

# Add Files
COPY sigma-cli /opt/sigma-cli
# Change Directory
WORKDIR /opt/sigma-cli

# Install Python Modules
RUN set -eux; \
  python -m pipx install sigma-cli; \

# Execute sigma
CMD ["sigma"]
