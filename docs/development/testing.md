# Testing Guide

Comprehensive testing guidelines for Consoul's three-layer architecture. Different layers require different testing approaches to ensure quality without coupling tests to implementation details.

## Testing Philosophy

### Goals

1. **Fast Feedback** - Tests should run quickly for rapid iteration
2. **Isolation** - Test units in isolation from dependencies
3. **Coverage** - High coverage of business logic in services
4. **Confidence** - Integration tests verify layers work together
5. **Maintainability** - Tests should be easy to update as code evolves

### Layer-Specific Strategies

| Layer | Test Type | Focus | Tools |
|-------|-----------|-------|-------|
| SDK | Unit Tests | Business logic with mocked dependencies | pytest, unittest.mock |
| TUI | Integration Tests | Widget behavior and user interaction | Textual test harness, pytest |
| CLI | Command Tests | Argument parsing and output | Typer test utils, pytest |

## SDK Layer Testing

### Unit Testing Services

**Goal**: Test business logic in isolation without real AI models or databases

**Pattern**: Mock all external dependencies

**Example**: Testing ConversationService

```python
# tests/unit/sdk/services/test_conversation.py

import pytest
from unittest.mock import AsyncMock, Mock, patch
from consoul.sdk.services import ConversationService
from consoul.sdk.models import Token

@pytest.fixture
def mock_model():
    """Mock LangChain chat model."""
    model = Mock()

    # Mock streaming response
    model.stream = Mock(return_value=iter([
        Mock(content="Hello", tool_calls=[], usage_metadata=None),
        Mock(content=" world", tool_calls=[], usage_metadata=None)
    ]))

    return model

@pytest.fixture
def mock_conversation():
    """Mock conversation history."""
    conversation = Mock()
    conversation.messages = []
    conversation.max_tokens = 128000
    conversation.add_user_message_async = AsyncMock()
    conversation._persist_message = AsyncMock()
    return conversation

@pytest.fixture
def mock_tool_registry():
    """Mock tool registry."""
    registry = Mock()
    registry.list_tools = Mock(return_value=[])
    return registry

@pytest.mark.asyncio
async def test_send_message_streams_tokens(
    mock_model, mock_conversation, mock_tool_registry
):
    """Test that send_message yields streaming tokens."""
    # Create service with mocked dependencies
    service = ConversationService(
        model=mock_model,
        conversation=mock_conversation,
        tool_registry=mock_tool_registry
    )

    # Send message and collect tokens
    tokens = []
    async for token in service.send_message("Hi"):
        tokens.append(token.content)

    # Verify streaming behavior
    assert tokens == ["Hello", " world"]
    assert "".join(tokens) == "Hello world"

    # Verify conversation was updated
    mock_conversation.add_user_message_async.assert_called_once_with("Hi")

@pytest.mark.asyncio
async def test_send_message_with_tool_approval(
    mock_model, mock_conversation, mock_tool_registry
):
    """Test tool execution approval workflow."""
    # Setup tool call in response
    tool_call_chunk = Mock(
        content="",
        tool_calls=[{
            "name": "bash_execute",
            "args": {"command": "ls"},
            "id": "call_123",
            "type": "tool_call"
        }],
        usage_metadata=None
    )

    mock_model.stream = Mock(return_value=iter([tool_call_chunk]))

    # Mock tool registry
    mock_tool = Mock()
    mock_tool.name = "bash_execute"
    mock_tool.invoke = Mock(return_value="file1.py\nfile2.py")

    mock_tool_meta = Mock()
    mock_tool_meta.tool = mock_tool
    mock_tool_meta.risk_level = Mock(value="caution")

    mock_tool_registry.list_tools = Mock(return_value=[mock_tool_meta])

    # Create approval callback
    approval_callback = AsyncMock(return_value=True)

    # Create service
    service = ConversationService(
        model=mock_model,
        conversation=mock_conversation,
        tool_registry=mock_tool_registry
    )

    # Send message with approval callback
    tokens = []
    async for token in service.send_message(
        "List files",
        on_tool_request=approval_callback
    ):
        tokens.append(token.content)

    # Verify approval was requested
    approval_callback.assert_called_once()
    request = approval_callback.call_args[0][0]
    assert request.name == "bash_execute"
    assert request.risk_level == "caution"
```

### Testing with Fixtures

**Pattern**: Create reusable fixtures for common mocks

```python
# tests/conftest.py

import pytest
from unittest.mock import Mock, AsyncMock

@pytest.fixture
def mock_config():
    """Mock Consoul configuration."""
    config = Mock()
    config.current_model = "gpt-4o"
    config.current_provider = Mock(value="openai")
    config.tools = Mock(enabled=True)
    return config

@pytest.fixture
def mock_chat_model():
    """Mock LangChain chat model with common behavior."""
    model = Mock()
    model.stream = Mock(return_value=iter([
        Mock(content="Response", tool_calls=[], usage_metadata=None)
    ]))
    model.ainvoke = AsyncMock(return_value=Mock(content="Response"))
    return model
```

### Testing Async Methods

**Pattern**: Use `pytest-asyncio` for async test functions

```python
import pytest

@pytest.mark.asyncio
async def test_async_service_method():
    """Test async service method."""
    service = MyService()
    result = await service.async_method()
    assert result == expected_value
```

### Testing Error Handling

**Pattern**: Verify services handle errors gracefully

```python
@pytest.mark.asyncio
async def test_service_handles_model_error(mock_model, mock_conversation):
    """Test service handles model errors without crashing."""
    # Mock model to raise error
    mock_model.stream = Mock(side_effect=Exception("API error"))

    service = ConversationService(
        model=mock_model,
        conversation=mock_conversation
    )

    # Verify error is handled
    with pytest.raises(Exception) as exc_info:
        async for token in service.send_message("Hi"):
            pass

    assert "API error" in str(exc_info.value)
```

## TUI Layer Testing

### Integration Testing Widgets

**Goal**: Test UI components work correctly with Textual framework

**Pattern**: Use Textual's test harness for widget testing

**Example**: Testing chat widget

```python
# tests/integration/tui/test_chat_widget.py

import pytest
from textual.widgets import Input
from consoul.tui.widgets import ChatDisplay
from consoul.tui.app import ConsoulApp

@pytest.mark.integration
async def test_chat_widget_displays_message():
    """Test chat widget displays user message."""
    app = ConsoulApp()

    async with app.run_test() as pilot:
        # Get chat display widget
        chat = app.query_one(ChatDisplay)

        # Simulate user input
        input_widget = app.query_one(Input)
        input_widget.value = "Hello AI"
        await pilot.press("enter")

        # Verify message appears in chat
        assert "Hello AI" in chat.text

@pytest.mark.integration
async def test_modal_approval_flow():
    """Test tool approval modal workflow."""
    app = ConsoulApp()

    async with app.run_test() as pilot:
        # Trigger tool execution that needs approval
        input_widget = app.query_one(Input)
        input_widget.value = "Run ls command"
        await pilot.press("enter")

        # Wait for approval modal
        await pilot.pause(0.5)

        # Verify modal appeared
        from consoul.tui.modals import ToolApprovalModal
        modal = app.screen.query_one(ToolApprovalModal)
        assert modal is not None

        # Approve tool
        await pilot.click("#approve-button")

        # Verify tool executed and result displayed
        chat = app.query_one(ChatDisplay)
        assert "file1.py" in chat.text  # Expected output
```

### Testing Screen Navigation

```python
@pytest.mark.integration
async def test_screen_navigation():
    """Test switching between screens."""
    app = ConsoulApp()

    async with app.run_test() as pilot:
        # Start on main screen
        assert app.screen.name == "main"

        # Navigate to settings
        await pilot.press("ctrl+s")
        assert app.screen.name == "settings"

        # Navigate back
        await pilot.press("escape")
        assert app.screen.name == "main"
```

### Mocking Service Layer in TUI Tests

**Pattern**: Mock services to test UI in isolation

```python
from unittest.mock import AsyncMock, Mock, patch

@pytest.mark.integration
async def test_tui_with_mocked_service():
    """Test TUI with mocked ConversationService."""

    # Create mock service
    mock_service = Mock()
    mock_service.send_message = AsyncMock(return_value=iter([
        Mock(content="Mocked response", cost=None)
    ]))

    # Patch service creation
    with patch(
        'consoul.sdk.services.ConversationService.from_config',
        return_value=mock_service
    ):
        app = ConsoulApp()

        async with app.run_test() as pilot:
            # Send message
            input_widget = app.query_one(Input)
            input_widget.value = "Test"
            await pilot.press("enter")

            # Verify mock was called
            mock_service.send_message.assert_called_once_with("Test")
```

## CLI Layer Testing

### Testing Commands

**Goal**: Test command parsing and execution

**Pattern**: Use Typer's CliRunner

**Example**: Testing chat command

```python
# tests/cli/test_history_commands.py

from typer.testing import CliRunner
from consoul.cli.main import app

runner = CliRunner()

def test_chat_command_basic():
    """Test basic chat command."""
    result = runner.invoke(app, ["chat", "Hello"])

    assert result.exit_code == 0
    assert "Hello" in result.stdout

def test_chat_command_with_model():
    """Test chat command with model flag."""
    result = runner.invoke(app, [
        "chat",
        "--model", "gpt-4o",
        "Hello"
    ])

    assert result.exit_code == 0
    # Verify model was used (check output or mock)
```

### Testing Output Formatting

```python
def test_command_json_output():
    """Test command outputs valid JSON."""
    result = runner.invoke(app, ["list-models", "--format", "json"])

    assert result.exit_code == 0

    # Verify valid JSON
    import json
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert len(data) > 0
```

## Test Organization

### Directory Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Fast, isolated tests
│   ├── sdk/
│   │   ├── services/
│   │   │   ├── test_conversation.py
│   │   │   ├── test_tool.py
│   │   │   └── test_model.py
│   │   └── test_models.py
│   ├── ai/
│   │   ├── test_history.py
│   │   └── test_tools.py
│   └── cli/
│       └── test_commands.py
├── integration/             # Slower, real dependencies
│   ├── tui/
│   │   ├── test_app.py
│   │   └── test_widgets.py
│   └── sdk/
│       └── test_full_workflow.py
└── e2e/                     # End-to-end tests
    └── test_user_scenarios.py
```

### Fixture Organization

**Pattern**: Place fixtures close to where they're used

```python
# tests/unit/sdk/services/conftest.py - Service-specific fixtures

import pytest
from unittest.mock import Mock, AsyncMock

@pytest.fixture
def mock_model():
    """Mock for service layer tests."""
    ...

# tests/conftest.py - Global fixtures

@pytest.fixture
def temp_config_file(tmp_path):
    """Create temporary config file."""
    config_file = tmp_path / "config.toml"
    config_file.write_text("""
    [core]
    current_model = "gpt-4o"
    """)
    return config_file
```

## Running Tests

### Run All Tests

```bash
make test
# or
poetry run pytest -v --cov
```

### Run Unit Tests Only

```bash
poetry run pytest tests/unit/ -v
```

### Run Integration Tests Only

```bash
poetry run pytest tests/integration/ -m integration -v
```

### Run Specific Test File

```bash
poetry run pytest tests/unit/sdk/services/test_conversation.py -v
```

### Run Tests with Coverage

```bash
poetry run pytest --cov=src/consoul --cov-report=html
# Open htmlcov/index.html in browser
```

### Run Tests in Watch Mode

```bash
poetry run pytest-watch
```

## Coverage Requirements

### Target Coverage

- **SDK Layer**: 90%+ coverage (critical business logic)
- **TUI Layer**: 60%+ coverage (harder to test, less critical)
- **CLI Layer**: 70%+ coverage (important for usability)

### Checking Coverage

```bash
make test
# View report: htmlcov/index.html

# Or check specific module
poetry run pytest --cov=src/consoul/sdk/services/conversation --cov-report=term-missing
```

## Common Testing Patterns

### Testing AsyncIterators

**Pattern**: Collect yielded values into list

```python
@pytest.mark.asyncio
async def test_async_iterator():
    """Test async iterator yields expected values."""
    service = MyService()

    results = []
    async for item in service.stream_items():
        results.append(item)

    assert results == ["item1", "item2", "item3"]
```

### Testing with Timeouts

**Pattern**: Use pytest timeout for long-running tests

```python
@pytest.mark.timeout(5)  # Fail if test takes > 5 seconds
@pytest.mark.asyncio
async def test_service_completes_quickly():
    """Test service responds within reasonable time."""
    service = MyService()
    result = await service.quick_method()
    assert result is not None
```

### Parametrized Tests

**Pattern**: Test multiple scenarios with same test logic

```python
@pytest.mark.parametrize("model_id,expected_provider", [
    ("gpt-4o", "openai"),
    ("claude-3-5-sonnet-20241022", "anthropic"),
    ("gemini-pro", "google"),
])
def test_model_provider_detection(model_id, expected_provider):
    """Test model provider is correctly detected."""
    service = ModelService()
    provider = service._detect_provider(model_id)
    assert provider == expected_provider
```

### Testing Callbacks

**Pattern**: Use AsyncMock to verify callback invocations

```python
@pytest.mark.asyncio
async def test_callback_is_called():
    """Test service calls callback with correct arguments."""
    # Create mock callback
    callback = AsyncMock(return_value=True)

    service = ConversationService(...)

    # Execute code that should call callback
    async for token in service.send_message("Hi", on_tool_request=callback):
        pass

    # Verify callback was called
    callback.assert_called_once()

    # Check arguments
    args, kwargs = callback.call_args
    assert args[0].name == "expected_tool_name"
```

## Continuous Integration

### GitHub Actions

**Pattern**: Run tests on every PR

```yaml
# .github/workflows/test.yml

name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install --with dev
      - name: Run tests
        run: poetry run pytest --cov --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Best Practices

### ✅ Do:

- **Test Behavior, Not Implementation** - Test what, not how
- **Use Descriptive Test Names** - `test_service_handles_model_error_gracefully`
- **Arrange-Act-Assert Pattern** - Clear test structure
- **Mock External Dependencies** - Services shouldn't call real APIs in tests
- **Test Error Paths** - Verify error handling works
- **Keep Tests Fast** - Unit tests should be under 100ms each
- **Test Edge Cases** - Empty inputs, None values, boundaries

### ❌ Don't:

- **Test Private Methods** - Test public API only
- **Write Flaky Tests** - Tests should be deterministic
- **Skip Integration Tests** - Services need integration tests too
- **Test Implementation Details** - Tests break when refactoring
- **Use Sleep in Tests** - Use proper async/await
- **Share State Between Tests** - Each test should be isolated

## Debugging Tests

### Print Debugging

```python
def test_something(capfd):
    """Test with captured output."""
    service.do_something()

    # Capture printed output
    captured = capfd.readouterr()
    assert "expected text" in captured.out
```

### Pytest Debugging

```bash
# Run with print output visible
poetry run pytest -s

# Drop into debugger on failure
poetry run pytest --pdb

# Run last failed test
poetry run pytest --lf

# Run with verbose output
poetry run pytest -vv
```

### Async Debugging

```python
import asyncio

@pytest.mark.asyncio
async def test_async_debug():
    """Debug async test."""
    # Enable asyncio debug mode
    asyncio.get_event_loop().set_debug(True)

    service = MyService()
    result = await service.async_method()

    assert result is not None
```

## Examples

See these test files for reference:

- **Service Unit Tests**: `tests/unit/sdk/services/test_conversation.py` (SOUL-256)
- **SDK Headless Tests**: `tests/unit/sdk/test_sdk_headless.py` (SOUL-278)
- **TUI Integration Tests**: `tests/integration/tui/test_app.py`
- **CLI Command Tests**: `tests/cli/test_history_commands.py`

## Next Steps

- **[Architecture Guide](architecture.md)** - Understanding what to test at each layer
- **[Service Layer Guide](service-layer.md)** - How to design testable services
- **[Contributing Guide](../contributing.md)** - PR requirements including tests
