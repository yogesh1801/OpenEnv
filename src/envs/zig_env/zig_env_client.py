# Copyright (c) Yogesh Singla and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Zig Environment HTTP Client.

This module provides the client for connecting to a Zig Environment server
over HTTP.
"""

from typing import Dict

from core.client_types import StepResult
from core.http_env_client import HTTPEnvClient

from .models import ZigAction, ZigObservation, ZigState


class ZigEnv(HTTPEnvClient[ZigAction, ZigObservation]):
    """
    HTTP client for the Zig Environment.
    
    This client connects to a ZigEnvironment HTTP server and provides
    methods to interact with it: reset(), step(), and state access.
    
    Example:
        >>> # Connect to a running server
        >>> client = ZigEnv(base_url="http://localhost:8000")
        >>> result = client.reset()
        >>> print(result.observation.stdout)
        >>>
        >>> # Execute Zig code
        >>> action = ZigAction(
        ...     core_code='const std = @import("std");\\nfn multiply(a: i32, b: i32) i32 { return a * b; }',
        ...     test_code='test "multiply" { try std.testing.expectEqual(@as(i32, 12), multiply(3, 4)); }'
        ... )
        >>> result = client.step(action)
        >>> print(result.observation.tests_passed)  # 1
        >>> print(result.reward)

    Example with Docker:
        >>> # Automatically start container and connect
        >>> client = ZigEnv.from_docker_image("zig-env:latest")
        >>> result = client.reset()
        >>> result = client.step(ZigAction(
        ...     core_code='const std = @import("std");\\npub fn main() void { std.debug.print("4\\n", .{}); }',
        ...     test_code=''
        ... ))
        >>> print(result.observation.stdout)  # "4\n"
        >>> client.close()
    """

    def _step_payload(self, action: ZigAction) -> Dict:
        """
        Convert ZigAction to JSON payload for step request.
        
        Args:
            action: ZigAction instance
            
        Returns:
            Dictionary representation suitable for JSON encoding
        """
        return {
            "core_code": action.core_code,
            "test_code": action.test_code
        }

    def _parse_result(self, payload: Dict) -> StepResult[ZigObservation]:
        """
        Parse server response into StepResult[ZigObservation].
        
        Args:
            payload: JSON response from server
            
        Returns:
            StepResult with ZigObservation
        """
        obs_data = payload.get("observation", {})
        observation = ZigObservation(
            stdout=obs_data.get("stdout", ""),
            stderr=obs_data.get("stderr", ""),
            exit_code=obs_data.get("exit_code", 0),
            tests_passed=obs_data.get("tests_passed", 0),
            tests_failed=obs_data.get("tests_failed", 0),
            code_compiles=obs_data.get("code_compiles", True),
            metadata=obs_data.get("metadata", {}),
        )
        
        return StepResult[ZigObservation](
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> ZigState:
        """
        Parse server response into ZigState object.
        
        Args:
            payload: JSON response from /state endpoint
            
        Returns:
            ZigState object with episode metadata
        """
        return ZigState(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
            last_exit_code=payload.get("last_exit_code", 0),
            last_code_compiles=payload.get("last_code_compiles", True),
            total_tests_passed=payload.get("total_tests_passed", 0),
            total_tests_failed=payload.get("total_tests_failed", 0),
        )

