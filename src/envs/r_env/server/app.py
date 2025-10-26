# Copyright (c) Yogesh Singla and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
FastAPI application for the R Environment.

This module creates an HTTP server that exposes the RCodeActEnv
over HTTP endpoints, making it compatible with HTTPEnvClient.

Usage:
    # Development (with auto-reload):
    uvicorn envs.r_env.server.app:app --reload --host 0.0.0.0 --port 8000

    # Production:
    uvicorn envs.r_env.server.app:app --host 0.0.0.0 --port 8000 --workers 4

    # Or run directly:
    python -m envs.r_env.server.app
"""

from core.env_server import create_app

from ..models import RAction, RObservation
from .r_codeact_env import RCodeActEnv

# Create the environment instance
env = RCodeActEnv()

# Create the app with web interface and README integration
app = create_app(env, RAction, RObservation, env_name="r_env")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

