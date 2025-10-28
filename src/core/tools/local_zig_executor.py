# Copyright (c) Yogesh Singla and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Local Zig Executor.

This module provides functionality for executing Zig code locally using
subprocess, similar to PyExecutor and JuliaExecutor.
"""

import subprocess
import tempfile
import os
from pathlib import Path

from core.env_server.types import CodeExecResult


class ZigExecutor:
    """
    Executor for running Zig code in a subprocess.
    
    This class provides a simple interface to execute Zig code in isolation
    and capture the results including stdout, stderr, and exit code.
    
    Example:
        >>> executor = ZigExecutor()
        >>> result = executor.run('const std = @import("std");\\npub fn main() void { std.debug.print("Hello, Zig!\\n", .{}); }')
        >>> print(result.stdout)  # "Hello, Zig!\n"
        >>> print(result.exit_code)  # 0
        >>>
        >>> # With tests
        >>> code = '''
        ... const std = @import("std");
        ... fn add(a: i32, b: i32) i32 {
        ...     return a + b;
        ... }
        ... test "add function" {
        ...     try std.testing.expectEqual(@as(i32, 5), add(2, 3));
        ... }
        ... '''
        >>> result = executor.run(code)
        >>> print(result.exit_code)  # 0
    """
    
    def __init__(self, timeout: int = 60):
        """
        Initialize the ZigExecutor.
        
        Args:
            timeout: Maximum execution time in seconds (default: 60)
        """
        self.timeout = timeout
    
    def run(self, code: str) -> CodeExecResult:
        """
        Execute Zig code and return the result.
        
        Args:
            code: Zig code string to execute
            
        Returns:
            CodeExecResult containing stdout, stderr, and exit_code
            
        Example:
            >>> executor = ZigExecutor()
            >>> result = executor.run('const std = @import("std");\\npub fn main() void { std.debug.print("8\\n", .{}); }')
            >>> print(result.stdout)  # "8\n"
            >>> print(result.exit_code)  # 0
            >>>
            >>> # Error handling
            >>> result = executor.run("invalid zig code")
            >>> print(result.exit_code)  # 1
            >>> print(result.stderr)  # Contains error message
        """

        try:
            # Create temporary directory for Zig project
            with tempfile.TemporaryDirectory() as tmpdir:
                code_file = os.path.join(tmpdir, 'main.zig')
                
                # Write code to file
                with open(code_file, 'w', encoding='utf-8') as f:
                    f.write(code)
                
                try:
                    # First, try to run tests if they exist
                    if 'test ' in code:
                        # Run zig test
                        result = subprocess.run(
                            ['zig', 'test', code_file],
                            capture_output=True,
                            text=True,
                            timeout=self.timeout,
                            cwd=tmpdir,
                        )
                    else:
                        # Run regular code (compile and run)
                        result = subprocess.run(
                            ['zig', 'run', code_file],
                            capture_output=True,
                            text=True,
                            timeout=self.timeout,
                            cwd=tmpdir,
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
                stderr=f"Error executing Zig code: {str(e)}",
                exit_code=-1,
            )

