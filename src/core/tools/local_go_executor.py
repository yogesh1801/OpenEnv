# Copyright (c) Yogesh Singla and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Local Go Executor.

This module provides functionality for executing Go code locally using
subprocess, similar to JuliaExecutor.
"""

import subprocess
import tempfile
import os
from pathlib import Path

from core.env_server.types import CodeExecResult


class GoExecutor:
    """
    Executor for running Go code in a subprocess.
    
    This class provides a simple interface to execute Go code in isolation
    and capture the results including stdout, stderr, and exit code.
    
    Example:
        >>> executor = GoExecutor()
        >>> result = executor.run('package main\\n\\nimport "fmt"\\n\\nfunc main() {\\n    fmt.Println("Hello, Go!")\\n}')
        >>> print(result.stdout)  # "Hello, Go!\n"
        >>> print(result.exit_code)  # 0
        >>>
        >>> # With tests
        >>> core_code = '''package main
        ... 
        ... func Add(a, b int) int {
        ...     return a + b
        ... }
        ... '''
        >>> test_code = '''package main
        ... 
        ... import "testing"
        ... 
        ... func TestAdd(t *testing.T) {
        ...     if Add(2, 3) != 5 {
        ...         t.Error("Expected 5")
        ...     }
        ... }
        ... '''
        >>> result = executor.run_with_tests(core_code, test_code)
        >>> print(result.exit_code)  # 0
    """
    
    def __init__(self, timeout: int = 60):
        """
        Initialize the GoExecutor.
        
        Args:
            timeout: Maximum execution time in seconds (default: 60)
        """
        self.timeout = timeout
    
    def run(self, code: str) -> CodeExecResult:
        """
        Execute Go code and return the result.
        
        Args:
            code: Go code string to execute (must include package main and main function for executables)
            
        Returns:
            CodeExecResult containing stdout, stderr, and exit_code
            
        Example:
            >>> executor = GoExecutor()
            >>> result = executor.run('package main\\n\\nimport "fmt"\\n\\nfunc main() {\\n    fmt.Println(5 + 3)\\n}')
            >>> print(result.stdout)  # "8\n"
            >>> print(result.exit_code)  # 0
            >>>
            >>> # Error handling
            >>> result = executor.run('invalid go code')
            >>> print(result.exit_code)  # 1
            >>> print(result.stderr)  # Contains error message
        """

        # Create a temporary directory for Go module
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            try:
                # Write the Go code to a file
                code_file = tmppath / "main.go"
                code_file.write_text(code, encoding='utf-8')
                
                # Initialize go module
                init_result = subprocess.run(
                    ['go', 'mod', 'init', 'tempmodule'],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
                
                # Run the Go code
                result = subprocess.run(
                    ['go', 'run', 'main.go'],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
                
                return CodeExecResult(
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exit_code=result.returncode,
                )
                
            except subprocess.TimeoutExpired:
                return CodeExecResult(
                    stdout="",
                    stderr=f"Execution timed out after {self.timeout} seconds",
                    exit_code=-1,
                )
                
            except Exception as e:
                return CodeExecResult(
                    stdout="",
                    stderr=f"Error executing Go code: {str(e)}",
                    exit_code=-1,
                )
    
    def run_with_tests(self, core_code: str, test_code: str) -> CodeExecResult:
        """
        Execute Go code with tests.
        
        Args:
            core_code: Main Go code (without main function, just functions to test)
            test_code: Go test code (using testing package)
            
        Returns:
            CodeExecResult containing test results
            
        Example:
            >>> executor = GoExecutor()
            >>> core = 'package main\\n\\nfunc Add(a, b int) int {\\n    return a + b\\n}'
            >>> test = 'package main\\n\\nimport "testing"\\n\\nfunc TestAdd(t *testing.T) {\\n    if Add(2, 3) != 5 {\\n        t.Error("Expected 5")\\n    }\\n}'
            >>> result = executor.run_with_tests(core, test)
            >>> print(result.exit_code)  # 0 if all tests pass
        """
        
        # Create a temporary directory for Go module
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            try:
                # Write the core code
                core_file = tmppath / "main.go"
                core_file.write_text(core_code, encoding='utf-8')
                
                # Write the test code
                test_file = tmppath / "main_test.go"
                test_file.write_text(test_code, encoding='utf-8')
                
                # Initialize go module
                init_result = subprocess.run(
                    ['go', 'mod', 'init', 'tempmodule'],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
                
                # Run the tests with verbose output
                result = subprocess.run(
                    ['go', 'test', '-v'],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
                
                return CodeExecResult(
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exit_code=result.returncode,
                )
                
            except subprocess.TimeoutExpired:
                return CodeExecResult(
                    stdout="",
                    stderr=f"Test execution timed out after {self.timeout} seconds",
                    exit_code=-1,
                )
                
            except Exception as e:
                return CodeExecResult(
                    stdout="",
                    stderr=f"Error executing Go tests: {str(e)}",
                    exit_code=-1,
                )


