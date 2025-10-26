# Go Environment

HTTP server for executing Go code with test result tracking and reward calculation.

## Overview

This environment provides a Go code execution environment through OpenEnv's HTTP interface. It executes Go code, runs tests using the `testing` package, and calculates rewards based on execution success and test outcomes.

## Features

- ✅ Execute Go code in isolated subprocess
- ✅ Parse `testing` package output (tests passed/failed)
- ✅ Calculate rewards based on execution results
- ✅ Safety transforms for dangerous operations
- ✅ Docker support for reproducible execution
- ✅ Compatible with GRPO training

## Quick Start

### Using Docker (Recommended)

```bash
# From OpenEnv root directory

# 1. Build base image (one-time)
docker build -t openenv-base:latest -f src/core/containers/images/Dockerfile .

# 2. Build Go environment image
docker build -t go-env:latest -f src/envs/go_env/server/Dockerfile .

# 3. Run the server
docker run -d -p 8000:8000 --name go-env-server go-env:latest

# 4. Test the server
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

### Using Python Client

```python
from envs.go_env import GoEnv, GoAction

# Connect to server
env = GoEnv(base_url="http://localhost:8000")

# Reset environment
result = env.reset()

# Execute Go code with tests
core_code = """package main

func Add(a, b int) int {
    return a + b
}
"""

test_code = """package main

import "testing"

func TestAdd(t *testing.T) {
    if Add(2, 3) != 5 {
        t.Error("Expected 5")
    }
    if Add(10, 20) != 30 {
        t.Error("Expected 30")
    }
}
"""

action = GoAction(core_code=core_code, test_code=test_code)
result = env.step(action)

print(f"Exit code: {result.observation.exit_code}")
print(f"Tests passed: {result.observation.tests_passed}")
print(f"Tests failed: {result.observation.tests_failed}")
print(f"Reward: {result.reward}")

# Close connection
env.close()
```

## API Endpoints

### Health Check
```
GET /health
Response: {"status": "healthy"}
```

### Reset Environment
```
POST /reset
Response: {
  "observation": {
    "stdout": "",
    "stderr": "",
    "exit_code": 0,
    "tests_passed": 0,
    "tests_failed": 0,
    "code_compiles": true,
    "reward": 0.0
  }
}
```

### Execute Code (Step)
```
POST /step
Body: {
  "core_code": "package main\n\nfunc Add(a, b int) int {\n    return a + b\n}",
  "test_code": "package main\n\nimport \"testing\"\n\nfunc TestAdd(t *testing.T) {\n    if Add(2, 3) != 5 {\n        t.Error(\"Expected 5\")\n    }\n}"
}

Response: {
  "observation": {
    "stdout": "=== RUN   TestAdd\n--- PASS: TestAdd (0.00s)\nPASS",
    "stderr": "",
    "exit_code": 0,
    "tests_passed": 1,
    "tests_failed": 0,
    "code_compiles": true,
    "reward": 7
  },
  "reward": 7,
  "done": false
}
```

### Get State
```
GET /state
Response: {
  "episode_id": "uuid",
  "step_count": 5,
  "last_exit_code": 0,
  "last_code_compiles": true,
  "total_tests_passed": 10,
  "total_tests_failed": 2
}
```

## Reward Structure

The environment calculates integer rewards based on:

- **Code doesn't compile**: `-3`
- **Code compiles**: `+1`
- **All tests pass (and at least 1 test)**: `+7` (total)
- **Some tests pass**: `+1 + 3 × tests_passed - 1 × tests_failed`

Examples:
```go
// Code doesn't compile
reward = -3

// Code compiles, no tests
reward = 1

// Code compiles, 3 tests pass, 0 fail
reward = 1 + 6 = 7

// Code compiles, 2 tests pass, 1 fails
reward = 1 + 3×2 - 1×1 = 6
```

## Test Parsing

The environment parses Go's `testing` package output:

### Individual Test Results
```
=== RUN   TestAdd
--- PASS: TestAdd (0.00s)
=== RUN   TestMultiply
--- FAIL: TestMultiply (0.00s)
```
→ tests_passed=1, tests_failed=1

### Overall Results
```
PASS
ok  	package	0.001s
```
→ All tests passed

```
FAIL
FAIL	package	0.001s
```
→ Some tests failed

## Safety Transforms

The environment includes safety transforms that penalize dangerous operations:

- File operations: `os.Remove`, `os.RemoveAll`, `os.Create`, etc.
- Process operations: `os.Exit`, `os.Exec`, `exec.Command`
- Network operations: `http.Get`, `http.Post`, `net.Dial`
- Unsafe operations: `unsafe.*`, `syscall.*`

Penalty: `-3.0` reward

## Docker Commands

### Development

```bash
# View logs
docker logs go-env-server
docker logs -f go-env-server  # Follow logs

# Stop/start container
docker stop go-env-server
docker start go-env-server

# Remove container
docker rm -f go-env-server

# Rebuild after code changes
docker build -t go-env:latest -f src/envs/go_env/server/Dockerfile .
docker rm -f go-env-server
docker run -d -p 8000:8000 --name go-env-server go-env:latest

# Interactive debugging
docker exec -it go-env-server /bin/bash
```

### Verify Installation

```bash
# Check Go version inside container
docker exec go-env-server go version
# Expected: go version go1.21.5 linux/amd64
```

## Local Development (Without Docker)

### Prerequisites

- Python 3.10+
- Go 1.21+ installed and in PATH
- FastAPI and dependencies

### Install Go

**Linux/macOS:**
```bash
wget https://go.dev/dl/go1.21.5.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.21.5.linux-amd64.tar.gz
export PATH=$PATH:/usr/local/go/bin
```

**Or download from:** https://go.dev/dl/

### Install Python Dependencies

```bash
pip install fastapi uvicorn
```

### Run Server Locally

```bash
# From OpenEnv root directory
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"
python -m envs.go_env.server.app
```

Server will start at: http://localhost:8000

## Example Usage

### Basic Example

```python
from envs.go_env import GoEnv, GoAction

# Connect to server
env = GoEnv(base_url="http://localhost:8000")

# Reset
result = env.reset()

# Simple function test
core_code = """package main

func Fibonacci(n int) int {
    if n <= 1 {
        return n
    }
    return Fibonacci(n-1) + Fibonacci(n-2)
}
"""

test_code = """package main

import "testing"

func TestFibonacci(t *testing.T) {
    tests := []struct {
        input    int
        expected int
    }{
        {0, 0},
        {1, 1},
        {5, 5},
        {10, 55},
    }
    
    for _, tt := range tests {
        result := Fibonacci(tt.input)
        if result != tt.expected {
            t.Errorf("Fibonacci(%d) = %d; want %d", tt.input, result, tt.expected)
        }
    }
}
"""

action = GoAction(core_code=core_code, test_code=test_code)
result = env.step(action)

print(f"Exit code: {result.observation.exit_code}")
print(f"Tests passed: {result.observation.tests_passed}")
print(f"Tests failed: {result.observation.tests_failed}")
print(f"Code compiles: {result.observation.code_compiles}")
print(f"Reward: {result.reward}")

# Close connection
env.close()
```

## GRPO Training Integration

This environment is designed for GRPO (Group Relative Policy Optimization) training:

```python
async def play_go_game(game_idx, game_id, server_url, policy, tokenizer):
    env = GoEnv(base_url=server_url)
    
    # Generate code with LLM
    prompt = format_go_prompt(task)
    responses = await policy.generate.route(prompt)
    
    # Extract core and test code
    core_code, test_code = extract_go_code(responses[0].text)
    
    # Execute in environment
    action = GoAction(core_code=core_code, test_code=test_code)
    result = env.step(action)
    
    # Get reward
    reward = result.observation.reward
    
    return {
        "prompt": prompt,
        "response": responses[0],
        "reward": reward,
        "tests_passed": result.observation.tests_passed,
        "tests_failed": result.observation.tests_failed,
        "code_compiles": result.observation.code_compiles
    }
```

See `examples/grpo_blackjack/` for a complete GRPO training example that can be adapted for Go.

## Configuration

### Environment Variables

- `PORT`: Server port (default: 8000)
- `HOST`: Server host (default: 0.0.0.0)
- `GO_TIMEOUT`: Go execution timeout in seconds (default: 60)

### Dockerfile Customization

To use a different Go version:

```dockerfile
# In Dockerfile, change the version
RUN wget -q https://go.dev/dl/go1.22.0.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.22.0.linux-amd64.tar.gz && \
    rm go1.22.0.linux-amd64.tar.gz
```

## Troubleshooting

### Go not found
```bash
# Verify Go is in PATH
go version

# In Docker, check installation
docker exec go-env-server go version
```

### Port already in use
```bash
# Use different port
docker run -p 8001:8000 --name go-env-server go-env:latest

# Update client base_url
env = GoEnv(base_url="http://localhost:8001")
```

### Container exits immediately
```bash
# Check logs
docker logs go-env-server

# Run in foreground to see errors
docker run -p 8000:8000 go-env:latest
```

### Build failures
```bash
# Clean build with no cache
docker build --no-cache -t go-env:latest -f src/envs/go_env/server/Dockerfile .

# Verbose output
docker build --progress=plain -t go-env:latest -f src/envs/go_env/server/Dockerfile .
```

## Architecture

```
┌─────────────────────────────────────┐
│   Python Client (HTTP)              │
│   GoEnv                             │
└────────────┬────────────────────────┘
             │ HTTP POST /step
             │ {"core_code": "...", "test_code": "..."}
             ▼
┌─────────────────────────────────────┐
│   FastAPI Server                    │
│   app.py                            │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│   GoCodeActEnv                      │
│   - Execute code via GoExecutor     │
│   - Parse test results              │
│   - Calculate rewards               │
│   - Apply transforms                │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│   GoExecutor (subprocess)           │
│   - Create temp directory           │
│   - Write main.go and main_test.go  │
│   - Run: go mod init && go test -v  │
│   - Capture stdout/stderr           │
│   - Return results                  │
└─────────────────────────────────────┘
```

## Development

### Code Structure

```
go_env/
├── __init__.py            # Package exports
├── models.py              # Data models (Action, Observation, State)
├── go_env_client.py       # HTTP client
├── README.md             # This file
└── server/
    ├── __init__.py       # Server package
    ├── app.py            # FastAPI server entry point
    ├── go_codeact_env.py # Environment implementation
    ├── go_transforms.py  # Safety and quality transforms
    └── Dockerfile        # Docker build instructions
```

### Running Tests

```bash
# Unit tests (when available)
pytest tests/envs/go_env/

# Manual integration test
python -c "
from envs.go_env import GoEnv, GoAction

env = GoEnv(base_url='http://localhost:8000')
result = env.reset()
print('Reset:', result.observation.exit_code)

action = GoAction(
    core_code='package main\\n\\nfunc Add(a, b int) int { return a + b }',
    test_code='package main\\n\\nimport \"testing\"\\n\\nfunc TestAdd(t *testing.T) { if Add(2,3) != 5 { t.Error(\"fail\") } }'
)
result = env.step(action)
print('Tests passed:', result.observation.tests_passed)
print('Reward:', result.reward)
"
```

## License

BSD-style license. See LICENSE file in repository root.


