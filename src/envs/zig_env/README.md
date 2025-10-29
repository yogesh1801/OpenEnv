# Zig Environment

An RL environment for Zig code execution and testing. This environment executes Zig code, runs tests using Zig's built-in test framework, and provides rewards based on code correctness and test results.

## Features

- **Code Execution**: Execute Zig code in an isolated environment
- **Testing Support**: Run tests using Zig's built-in test framework
- **Reward System**: Get rewards based on:
  - Code compilation/execution success
  - Number of tests passed
  - Number of tests failed
- **Safety Transforms**: Prevents dangerous operations (C imports, file deletion, system calls, etc.)
- **Quality Transforms**: Rewards concise, high-quality code

## Quick Start

### Local Usage

```python
from envs.zig_env import ZigEnv, ZigAction

# Connect to a running server
client = ZigEnv(base_url="http://localhost:8000")

# Reset the environment
result = client.reset()

# Execute Zig code with tests
action = ZigAction(
    core_code='''
const std = @import("std");

fn add(a: i32, b: i32) i32 {
    return a + b;
}

pub fn main() void {
    std.debug.print("Function defined\\n", .{});
}
''',
    test_code='''
test "add function works" {
    try std.testing.expectEqual(@as(i32, 5), add(2, 3));
    try std.testing.expectEqual(@as(i32, 0), add(-1, 1));
}
'''
)

result = client.step(action)
print(f"Tests passed: {result.observation.tests_passed}")
print(f"Tests failed: {result.observation.tests_failed}")
print(f"Reward: {result.reward}")
print(f"Output: {result.observation.stdout}")
```

### Docker Usage

```python
from envs.zig_env import ZigEnv, ZigAction

# Automatically start container and connect
client = ZigEnv.from_docker_image("zig-env:latest")

result = client.reset()
action = ZigAction(
    core_code='''
const std = @import("std");

fn multiply(x: i32, y: i32) i32 {
    return x * y;
}

pub fn main() void {}
''',
    test_code='''
test "multiply works" {
    try std.testing.expectEqual(@as(i32, 12), multiply(3, 4));
}
'''
)

result = client.step(action)
print(f"Reward: {result.reward}")
client.close()
```

## Building the Docker Image

```bash
# From the project root
docker build -t zig-env:latest -f src/envs/zig_env/server/Dockerfile .
```

## Running the Server

### Using Docker

```bash
docker run -p 8000:8000 zig-env:latest
```

### Using Python directly

```bash
# Make sure Zig is installed on your system
python -m envs.zig_env.server.app
```

Or with uvicorn:

```bash
uvicorn envs.zig_env.server.app:app --host 0.0.0.0 --port 8000
```

## Action/Observation Format

### ZigAction

```python
@dataclass
class ZigAction:
    core_code: str    # Core Zig code to execute
    test_code: str    # Test code using Zig's test framework
```

### ZigObservation

```python
@dataclass
class ZigObservation:
    stdout: str              # Standard output from execution
    stderr: str              # Standard error from execution
    exit_code: int           # Exit code (0 = success)
    tests_passed: int        # Number of tests passed
    tests_failed: int        # Number of tests failed
    code_compiles: bool      # Whether core code executed successfully
    reward: float            # Reward value
    metadata: dict           # Additional metadata
```

## Reward Structure

The environment provides rewards based on:

1. **Code Compilation** (-3 if fails, +1 if succeeds)
2. **Test Results**:
   - All tests pass: +2 bonus
   - Each test passed: +3
   - Each test failed: -1
3. **Code Quality**:
   - Concise code (≤120 chars): +1
   - Verbose code: -0.1
4. **Safety**:
   - Dangerous operations: -3

Example rewards:
- Code fails to compile: `-3`
- Code compiles, no tests: `+1`
- Code compiles, 3/3 tests pass: `+1 + 3*3 + 2 = +12`
- Code compiles, 2/3 tests pass: `+1 + 3*2 - 1*1 = +6`

## Testing with Zig

The environment supports Zig's built-in test framework:

```zig
const std = @import("std");

fn add(a: i32, b: i32) i32 {
    return a + b;
}

// Basic equality test
test "addition works" {
    try std.testing.expectEqual(@as(i32, 4), add(2, 2));
    try std.testing.expectEqual(@as(i32, 0), add(-1, 1));
}

// Test with floating point comparison
test "approximate equality" {
    const result: f32 = 0.1 + 0.2;
    try std.testing.expectApproxEqRel(@as(f32, 0.3), result, 0.01);
}

// Test error handling
test "expect error" {
    const result = someFunction();
    try std.testing.expectError(error.SomeError, result);
}

// Test boolean conditions
test "logical conditions" {
    try std.testing.expect(5 > 3);
    try std.testing.expect(!(2 > 10));
}
```

## Safety Features

The environment blocks dangerous operations:

- `@cImport`, `@cInclude`, `@cDefine` - C interop
- `std.os.exit`, `std.process.exit` - Process termination
- `std.fs.deleteFile`, `std.fs.deleteDir` - File/directory deletion
- `std.os.execve` - Execute programs
- `std.ChildProcess` - Child processes
- `@panic` - Explicit panics (though sometimes legitimate)

Attempting these operations will result in a penalty of -3 reward points.

## API Endpoints

When the server is running, it exposes:

- `POST /reset` - Reset the environment
- `POST /step` - Execute an action
- `GET /state` - Get current state
- `GET /health` - Health check
- `GET /` - Web interface

## Requirements

### System Requirements
- Zig (version 0.13.0 or higher)
- `zig` command available in PATH

### Python Requirements
- FastAPI
- uvicorn
- All dependencies from `core.env_server`

## Development

To extend the environment:

1. **Add new transforms**: Edit `server/zig_transforms.py`
2. **Modify reward function**: Edit `_calculate_reward()` in `server/zig_codeact_env.py`
3. **Update test parsing**: Edit `_parse_test_results()` in `server/zig_codeact_env.py`

## Examples

See `examples/` directory:
- `examples/local_zig_env.py` - Local usage without Docker
- `examples/zig_simple.py` - Docker-based usage

## Zig-Specific Notes

### Code Structure

Zig code requires proper structure:
- Use `const std = @import("std");` to import the standard library
- Define functions before using them
- Use `pub fn main()` for executable code
- Tests are automatically discovered by the test runner

### Type Annotations

Zig is statically typed and requires explicit type annotations:
```zig
const x: i32 = 42;           // Explicit type
const y = @as(f32, 3.14);    // Type coercion
```

### Memory Management

Zig requires explicit memory management. For simple examples, use:
```zig
var gpa = std.heap.GeneralPurposeAllocator(.{}){};
defer _ = gpa.deinit();
const allocator = gpa.allocator();
```

## License

BSD-style license. See LICENSE file in the root directory.

