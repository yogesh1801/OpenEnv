# R Environment

An RL environment for R code execution and testing. This environment executes R code, runs tests using the `testthat` package, and provides rewards based on code correctness and test results.

## Features

- **Code Execution**: Execute R code in an isolated environment
- **Testing Support**: Run tests using R's `testthat` package
- **Reward System**: Get rewards based on:
  - Code compilation/execution success
  - Number of tests passed
  - Number of tests failed
- **Safety Transforms**: Prevents dangerous operations (file deletion, system calls, etc.)
- **Quality Transforms**: Rewards concise, high-quality code

## Quick Start

### Local Usage

```python
from envs.r_env import REnv, RAction

# Connect to a running server
client = REnv(base_url="http://localhost:8000")

# Reset the environment
result = client.reset()

# Execute R code with tests
action = RAction(
    core_code='''
add <- function(a, b) {
    return(a + b)
}
''',
    test_code='''
library(testthat)
test_that("add function works", {
    expect_equal(add(2, 3), 5)
    expect_equal(add(-1, 1), 0)
})
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
from envs.r_env import REnv, RAction

# Automatically start container and connect
client = REnv.from_docker_image("r-env:latest")

result = client.reset()
action = RAction(
    core_code="multiply <- function(x, y) { x * y }",
    test_code="""
library(testthat)
test_that("multiply works", {
    expect_equal(multiply(3, 4), 12)
})
"""
)

result = client.step(action)
print(f"Reward: {result.reward}")
client.close()
```

## Building the Docker Image

```bash
# From the project root
docker build -t r-env:latest -f src/envs/r_env/server/Dockerfile .
```

## Running the Server

### Using Docker

```bash
docker run -p 8000:8000 r-env:latest
```

### Using Python directly

```bash
# Make sure R is installed on your system
python -m envs.r_env.server.app
```

Or with uvicorn:

```bash
uvicorn envs.r_env.server.app:app --host 0.0.0.0 --port 8000
```

## Action/Observation Format

### RAction

```python
@dataclass
class RAction:
    core_code: str    # Core R code to execute
    test_code: str    # Test code using testthat
```

### RObservation

```python
@dataclass
class RObservation:
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

1. **Code Compilation** (-3 if fails, 0 if succeeds)
2. **Test Results**:
   - All tests pass: +7 bonus
   - Each test passed: +3
   - Each test failed: -1
3. **Code Quality**:
   - Concise code (≤120 chars): +1
   - Verbose code: -0.1
4. **Safety**:
   - Dangerous operations: -3

Example rewards:
- Code fails to run: `-3`
- Code runs, no tests: `+1`
- Code runs, 3/3 tests pass: `+1 + 6 = +7`
- Code runs, 2/3 tests pass: `+1 + 3*2 - 1*1 = +6`

## Testing with testthat

The environment supports R's `testthat` package for unit testing:

```r
library(testthat)

# Test a function
test_that("addition works", {
    expect_equal(add(2, 2), 4)
    expect_equal(add(-1, 1), 0)
})

# Test for errors
test_that("division by zero fails", {
    expect_error(1/0)
})

# Test logical conditions
test_that("comparisons work", {
    expect_true(5 > 3)
    expect_false(2 > 10)
})
```

## Safety Features

The environment blocks dangerous operations:

- `system()`, `system2()`, `shell()` - System commands
- `file.remove()`, `unlink()` - File deletion
- `download.file()` - Network downloads
- `install.packages()` - Package installation
- `setwd()` - Working directory changes
- `.C()`, `.Call()`, `.External()` - Foreign function calls

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
- R (version 4.0 or higher)
- Rscript command available in PATH

### R Packages
- testthat (for testing)
- devtools (optional, for development)

### Python Requirements
- FastAPI
- uvicorn
- All dependencies from `core.env_server`

## Development

To extend the environment:

1. **Add new transforms**: Edit `server/r_transforms.py`
2. **Modify reward function**: Edit `_calculate_reward()` in `server/r_codeact_env.py`
3. **Update test parsing**: Edit `_parse_test_results()` in `server/r_codeact_env.py`

## Examples

See `examples/` directory for complete examples (to be added).

## License

BSD-style license. See LICENSE file in the root directory.

