# Copyright (c) Yogesh Singla, Inc. and affiliates.
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

# Install Zig using official tarball
RUN apt-get update && apt-get install -y \
    curl \
    xz-utils \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Zig 0.13.0 (latest stable version)
RUN curl -L https://ziglang.org/download/0.13.0/zig-linux-x86_64-0.13.0.tar.xz -o /tmp/zig.tar.xz \
    && tar -xf /tmp/zig.tar.xz -C /opt \
    && mv /opt/zig-linux-x86_64-0.13.0 /opt/zig \
    && rm /tmp/zig.tar.xz

# Add Zig to PATH
ENV PATH="/opt/zig:${PATH}"

# Verify Zig installation
RUN zig version

# Install smolagents for Python code execution utilities
RUN pip install --no-cache-dir smolagents

# Copy only what's needed for the Zig environment
COPY src/core/ /app/src/core/
COPY src/envs/zig_env/ /app/src/envs/zig_env/

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the FastAPI server
CMD ["uvicorn", "envs.zig_env.server.app:app", "--host", "0.0.0.0", "--port", "8000"]

