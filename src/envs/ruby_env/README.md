# Ruby Environment

An RL environment for Ruby code execution and testing. This environment executes Ruby code, runs tests using the Minitest framework, and provides rewards based on code correctness and test results.

## Features

- **Code Execution**: Execute Ruby code in an isolated environment
- **Testing Support**: Run tests using Ruby's Minitest framework
- **Reward System**: Get rewards based on:
  - Code compilation/execution success
  - Number of tests passed
  - Number of tests failed
- **Safety Transforms**: Prevents dangerous operations (shell commands, file deletion, network access, etc.)
- **Quality Transforms**: Rewards concise, high-quality code

## Quick Start

### Local Usage

```python
from envs.ruby_env import RubyEnv, RubyAction

# Connect to a running server
client = RubyEnv(base_url="http://localhost:8000")

# Reset the environment
result = client.reset()

# Execute Ruby code with tests
action = RubyAction(
    core_code='''
def add(a, b)
  a + b
end
''',
    test_code='''
require 'minitest/autorun'

class TestAdd < Minitest::Test
  def test_add
    assert_equal 5, add(2, 3)
  end
  
  def test_add_negative
    assert_equal 0, add(-1, 1)
  end
end
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
from envs.ruby_env import RubyEnv, RubyAction

# Automatically start container and connect
client = RubyEnv.from_docker_image("ruby-env:latest")

result = client.reset()
action = RubyAction(
    core_code="def multiply(x, y)\n  x * y\nend",
    test_code="""
require 'minitest/autorun'

class TestMultiply < Minitest::Test
  def test_multiply
    assert_equal 12, multiply(3, 4)
  end
end
"""
)

result = client.step(action)
print(f"Reward: {result.reward}")
client.close()
```

## Building the Docker Image

```bash
# From the project root
docker build -t ruby-env:latest -f src/envs/ruby_env/server/Dockerfile .
```

## Running the Server

### Using Docker

```bash
docker run -p 8000:8000 ruby-env:latest
```

### Using Python directly

```bash
# Make sure Ruby is installed on your system
python -m envs.ruby_env.server.app
```

Or with uvicorn:

```bash
uvicorn envs.ruby_env.server.app:app --host 0.0.0.0 --port 8000
```

## Action/Observation Format

### RubyAction

```python
@dataclass
class RubyAction:
    core_code: str    # Core Ruby code to execute
    test_code: str    # Test code using Minitest
```

### RubyObservation

```python
@dataclass
class RubyObservation:
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
- Code fails to run: `-3`
- Code runs, no tests: `+1`
- Code runs, 3/3 tests pass: `+1 + 3*3 + 2 = +12`
- Code runs, 2/3 tests pass: `+1 + 3*2 - 1*1 = +6`

## Testing with Minitest

The environment supports Ruby's Minitest framework for unit testing:

```ruby
require 'minitest/autorun'

# Define your class
class TestAddition < Minitest::Test
  def test_simple_addition
    assert_equal 4, add(2, 2)
  end
  
  def test_negative_numbers
    assert_equal 0, add(-1, 1)
  end
  
  def test_zero
    assert_equal 5, add(5, 0)
  end
end

# Test for errors
class TestDivision < Minitest::Test
  def test_division_by_zero
    assert_raises(ZeroDivisionError) { divide(1, 0) }
  end
end

# Test with refutations
class TestComparison < Minitest::Test
  def test_greater_than
    assert 5 > 3
    refute 2 > 10
  end
  
  def test_nil_values
    assert_nil nil
    refute_nil "not nil"
  end
end
```

### Common Minitest Assertions

- `assert_equal expected, actual` - Check equality
- `assert actual` - Check truthy value
- `refute actual` - Check falsy value
- `assert_nil obj` - Check for nil
- `assert_raises(Exception) { code }` - Check for exception
- `assert_in_delta expected, actual, delta` - Check floating point equality
- `assert_match pattern, string` - Check regex match
- `assert_includes collection, obj` - Check collection membership

## Safety Features

The environment blocks dangerous operations:

- `` ` `` (backticks) - Shell command execution
- `system()`, `exec()`, `spawn()` - System calls
- `eval()` - Dynamic code evaluation
- `File.delete`, `File.unlink`, `FileUtils.rm` - File deletion
- `Dir.delete` - Directory deletion
- `open()` with URLs - Network access
- `Net::HTTP`, `require 'open-uri'` - HTTP requests
- `IO.popen`, `Kernel.fork` - Process management

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
- Ruby (version 2.7 or higher)
- `ruby` command available in PATH

### Ruby Gems
- minitest (for testing)

### Python Requirements
- FastAPI
- uvicorn
- All dependencies from `core.env_server`

## Development

To extend the environment:

1. **Add new transforms**: Edit `server/ruby_transforms.py`
2. **Modify reward function**: Edit `_calculate_reward()` in `server/ruby_codeact_env.py`
3. **Update test parsing**: Edit `_parse_test_results()` in `server/ruby_codeact_env.py`

## Examples

See `examples/` directory:
- `examples/local_ruby_env.py` - Local usage without Docker
- `examples/ruby_simple.py` - Docker-based usage

## Ruby-Specific Notes

### Code Style

Ruby emphasizes readability and elegance:
```ruby
# Idiomatic Ruby
def greet(name)
  "Hello, #{name}!"
end

# Using blocks
[1, 2, 3].map { |n| n * 2 }

# Symbols as hash keys
person = { name: "Alice", age: 30 }
```

### Method Conventions

- Methods ending with `?` return boolean values
- Methods ending with `!` modify the object in-place
- Use `snake_case` for method and variable names

### Testing Conventions

- Test files typically use `test_` prefix for methods
- Group related tests in classes inheriting from `Minitest::Test`
- Use descriptive test names

## Common Ruby Patterns

### Iteration
```ruby
# Each
[1, 2, 3].each { |n| puts n }

# Map
squares = [1, 2, 3].map { |n| n ** 2 }

# Select/Filter
evens = [1, 2, 3, 4].select { |n| n.even? }

# Reduce
sum = [1, 2, 3].reduce(0) { |acc, n| acc + n }
```

### Classes and Objects
```ruby
class Person
  attr_accessor :name, :age
  
  def initialize(name, age)
    @name = name
    @age = age
  end
  
  def greet
    "Hello, I'm #{@name}"
  end
end
```

## License

BSD-style license. See LICENSE file in the root directory.

