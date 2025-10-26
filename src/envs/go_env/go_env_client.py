# Copyright (c) Yogesh Singla and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Go Environment HTTP Client.

This module provides the client for connecting to a Go Environment server
over HTTP.
"""

from typing import Dict

from core.client_types import StepResult
from core.http_env_client import HTTPEnvClient

from .models import GoAction, GoObservation, GoState


class GoEnv(HTTPEnvClient[GoAction, GoObservation]):
    """
    HTTP client for the Go Environment.
    
    This client connects to a GoEnvironment HTTP server and provides
    methods to interact with it: reset(), step(), and state access.
    
    Example:
        >>> # Connect to a running server
        >>> client = GoEnv(base_url="http://localhost:8000")
        >>> result = client.reset()
        >>> print(result.observation.stdout)
        >>>
        >>> # Execute Go code
        >>> action = GoAction(
        ...     core_code='package main\\n\\nfunc Multiply(a, b int) int {\\n    return a * b\\n}',
        ...     test_code='package main\\n\\nimport "testing"\\n\\nfunc TestMultiply(t *testing.T) {\\n    if Multiply(3, 4) != 12 {\\n        t.Error("Expected 12")\\n    }\\n}'
        ... )
        >>> result = client.step(action)
        >>> print(result.observation.tests_passed)  # 1
        >>> print(result.reward)

    Example with Docker:
        >>> # Automatically start container and connect
        >>> client = GoEnv.from_docker_image("go-env:latest")
        >>> result = client.reset()
        >>> result = client.step(GoAction(core_code='package main\\n\\nimport "fmt"\\n\\nfunc main() {\\n    fmt.Println(2 + 2)\\n}', test_code=''))
        >>> print(result.observation.stdout)  # "4\n"
        >>> client.close()
    """

    def _step_payload(self, action: GoAction) -> Dict:
        """
        Convert GoAction to JSON payload for step request.
        
        Args:
            action: GoAction instance
            
        Returns:
            Dictionary representation suitable for JSON encoding
        """
        return {
            "core_code": action.core_code,
            "test_code": action.test_code
        }

    def _parse_result(self, payload: Dict) -> StepResult[GoObservation]:
        """
        Parse server response into StepResult[GoObservation].
        
        Args:
            payload: JSON response from server
            
        Returns:
            StepResult with GoObservation
        """
        obs_data = payload.get("observation", {})
        observation = GoObservation(
            stdout=obs_data.get("stdout", ""),
            stderr=obs_data.get("stderr", ""),
            exit_code=obs_data.get("exit_code", 0),
            tests_passed=obs_data.get("tests_passed", 0),
            tests_failed=obs_data.get("tests_failed", 0),
            code_compiles=obs_data.get("code_compiles", True),
            metadata=obs_data.get("metadata", {}),
        )
        
        return StepResult[GoObservation](
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> GoState:
        """
        Parse server response into GoState object.
        
        Args:
            payload: JSON response from /state endpoint
            
        Returns:
            GoState object with episode metadata
        """
        return GoState(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
            last_exit_code=payload.get("last_exit_code", 0),
            last_code_compiles=payload.get("last_code_compiles", True),
            total_tests_passed=payload.get("total_tests_passed", 0),
            total_tests_failed=payload.get("total_tests_failed", 0),
        )


