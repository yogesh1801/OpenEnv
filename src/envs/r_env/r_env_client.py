# Copyright (c) Yogesh Singla and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
R Environment HTTP Client.

This module provides the client for connecting to an R Environment server
over HTTP.
"""

from typing import Dict

from core.client_types import StepResult
from core.http_env_client import HTTPEnvClient

from .models import RAction, RObservation, RState


class REnv(HTTPEnvClient[RAction, RObservation]):
    """
    HTTP client for the R Environment.
    
    This client connects to an REnvironment HTTP server and provides
    methods to interact with it: reset(), step(), and state access.
    
    Example:
        >>> # Connect to a running server
        >>> client = REnv(base_url="http://localhost:8000")
        >>> result = client.reset()
        >>> print(result.observation.stdout)
        >>>
        >>> # Execute R code
        >>> action = RAction(code='''
        ... multiply <- function(a, b) {
        ...     return(a * b)
        ... }
        ... 
        ... library(testthat)
        ... test_that("multiply works", {
        ...     expect_equal(multiply(3, 4), 12)
        ... })
        ... ''')
        >>> result = client.step(action)
        >>> print(result.observation.tests_passed)  # 1
        >>> print(result.reward)

    Example with Docker:
        >>> # Automatically start container and connect
        >>> client = REnv.from_docker_image("r-env:latest")
        >>> result = client.reset()
        >>> result = client.step(RAction(code="print(2 + 2)"))
        >>> print(result.observation.stdout)  # "[1] 4\n"
        >>> client.close()
    """

    def _step_payload(self, action: RAction) -> Dict:
        """
        Convert RAction to JSON payload for step request.
        
        Args:
            action: RAction instance
            
        Returns:
            Dictionary representation suitable for JSON encoding
        """
        return {
            "core_code": action.core_code,
            "test_code": action.test_code
        }

    def _parse_result(self, payload: Dict) -> StepResult[RObservation]:
        """
        Parse server response into StepResult[RObservation].
        
        Args:
            payload: JSON response from server
            
        Returns:
            StepResult with RObservation
        """
        obs_data = payload.get("observation", {})
        observation = RObservation(
            stdout=obs_data.get("stdout", ""),
            stderr=obs_data.get("stderr", ""),
            exit_code=obs_data.get("exit_code", 0),
            tests_passed=obs_data.get("tests_passed", 0),
            tests_failed=obs_data.get("tests_failed", 0),
            code_compiles=obs_data.get("code_compiles", True),
            metadata=obs_data.get("metadata", {}),
        )
        
        return StepResult[RObservation](
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> RState:
        """
        Parse server response into RState object.
        
        Args:
            payload: JSON response from /state endpoint
            
        Returns:
            RState object with episode metadata
        """
        return RState(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
            last_exit_code=payload.get("last_exit_code", 0),
            last_code_compiles=payload.get("last_code_compiles", True),
            total_tests_passed=payload.get("total_tests_passed", 0),
            total_tests_failed=payload.get("total_tests_failed", 0),
        )


