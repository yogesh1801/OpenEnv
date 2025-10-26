# Copyright (c) Yogesh Singla and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Local R Executor.

This module provides functionality for executing R code locally using
subprocess, similar to PyExecutor and JuliaExecutor.
"""

import subprocess
import tempfile
import os
from pathlib import Path

from core.env_server.types import CodeExecResult


class RExecutor:
    """
    Executor for running R code in a subprocess.
    
    This class provides a simple interface to execute R code in isolation
    and capture the results including stdout, stderr, and exit code.
    
    Example:
        >>> executor = RExecutor()
        >>> result = executor.run('print("Hello, R!")')
        >>> print(result.stdout)  # "[1] \"Hello, R!\"\n"
        >>> print(result.exit_code)  # 0
        >>>
        >>> # With tests
        >>> code = '''
        ... add <- function(a, b) {
        ...     return(a + b)
        ... }
        ... 
        ... library(testthat)
        ... test_that("add function works", {
        ...     expect_equal(add(2, 3), 5)
        ... })
        ... '''
        >>> result = executor.run(code)
        >>> print(result.exit_code)  # 0
    """
    
    def __init__(self, timeout: int = 60):
        """
        Initialize the RExecutor.
        
        Args:
            timeout: Maximum execution time in seconds (default: 60)
        """
        self.timeout = timeout
    
    def run(self, code: str) -> CodeExecResult:
        """
        Execute R code and return the result.
        
        Args:
            code: R code string to execute
            
        Returns:
            CodeExecResult containing stdout, stderr, and exit_code
            
        Example:
            >>> executor = RExecutor()
            >>> result = executor.run("x <- 5 + 3\\nprint(x)")
            >>> print(result.stdout)  # "[1] 8\n"
            >>> print(result.exit_code)  # 0
            >>>
            >>> # Error handling
            >>> result = executor.run("stop('error message')")
            >>> print(result.exit_code)  # 1
            >>> print(result.stderr)  # Contains error message
        """

        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.R',
                delete=False,
                encoding='utf-8'
            ) as f:
                f.write(code)
                code_file = f.name      
            try:
                result = subprocess.run(
                    ['Rscript', code_file],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
                
                return CodeExecResult(
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exit_code=result.returncode,
                )
                
            finally:
                try:
                    Path(code_file).unlink()
                except:
                    pass
                    
        except subprocess.TimeoutExpired:
            return CodeExecResult(
                stdout="",
                stderr=f"Execution timed out after {self.timeout} seconds",
                exit_code=-1,
            )
            
        except Exception as e:
            return CodeExecResult(
                stdout="",
                stderr=f"Error executing R code: {str(e)}",
                exit_code=-1,
            )


