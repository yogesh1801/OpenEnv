# Copyright (c) Yogesh Singla and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

# Use the standard openenv base image
# Built from: docker build -t openenv-base:latest -f src/core/containers/images/Dockerfile .
# In GitHub Actions, this is overridden to use the GHCR base image

# Use the standard openenv base image
ARG BASE_IMAGE=openenv-base:latest
FROM ${BASE_IMAGE}

# Install Go
RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Go 1.21 (latest stable)
RUN wget -q https://go.dev/dl/go1.21.5.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.21.5.linux-amd64.tar.gz && \
    rm go1.21.5.linux-amd64.tar.gz

# Add Go to PATH
ENV PATH="/usr/local/go/bin:${PATH}"
ENV GOPATH="/root/go"
ENV PATH="${GOPATH}/bin:${PATH}"

# Verify Go installation
RUN go version

# Install smolagents for Python code execution utilities (if needed)
RUN pip install --no-cache-dir smolagents

# Copy only what's needed for the Go environment
COPY src/core/ /app/src/core/
COPY src/envs/go_env/ /app/src/envs/go_env/

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the FastAPI server
CMD ["uvicorn", "envs.go_env.server.app:app", "--host", "0.0.0.0", "--port", "8000"]

