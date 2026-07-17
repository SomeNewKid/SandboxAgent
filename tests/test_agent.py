"""Tests for Sandbox Agent workloads."""

from pathlib import Path
from types import SimpleNamespace

from sandbox_agent import agent


def test_run_hello_world_writes_output_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify the minimal workload writes hello.txt and returns its message."""
    output_path = tmp_path / "hello.txt"
    monkeypatch.setattr(agent, "_HELLO_WORLD_OUTPUT_PATH", output_path)

    result = agent.run_hello_world()

    assert result == "Hello, World"
    assert output_path.read_text(encoding="utf-8") == "Hello, World"


def test_run_scrape_example_com_writes_output_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify the scrape workload writes scraped.txt and returns its content."""
    output_path = tmp_path / "scraped.txt"
    scraped_content = "<html><body>Example Domain</body></html>"
    monkeypatch.setattr(agent, "_SCRAPED_OUTPUT_PATH", output_path)
    monkeypatch.setattr(
        agent, "urlopen", lambda url, timeout: _FakeResponse(scraped_content)
    )

    result = agent.run_scrape_example_com()

    assert result == scraped_content
    assert output_path.read_text(encoding="utf-8") == scraped_content


def test_echo_environment_variable_writes_existing_value(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify an existing environment variable is echoed and saved."""
    output_path = tmp_path / "environment_variable.txt"
    monkeypatch.setattr(agent, "_ENVIRONMENT_VARIABLE_OUTPUT_PATH", output_path)
    monkeypatch.setenv("API_BASE_URL", "https://example.com")

    result = agent.echo_environment_variable("API_BASE_URL")

    assert result == "https://example.com"
    assert output_path.read_text(encoding="utf-8") == "https://example.com"


def test_echo_environment_variable_writes_missing_marker(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify a missing environment variable is echoed with a marker."""
    output_path = tmp_path / "environment_variable.txt"
    monkeypatch.setattr(agent, "_ENVIRONMENT_VARIABLE_OUTPUT_PATH", output_path)
    monkeypatch.delenv("API_BASE_URL", raising=False)

    result = agent.echo_environment_variable("API_BASE_URL")

    assert result == "[NO NAMED VARIABLE]"
    assert output_path.read_text(encoding="utf-8") == "[NO NAMED VARIABLE]"


def test_echo_environment_variable_writes_empty_marker(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify an empty environment variable is echoed with a marker."""
    output_path = tmp_path / "environment_variable.txt"
    monkeypatch.setattr(agent, "_ENVIRONMENT_VARIABLE_OUTPUT_PATH", output_path)
    monkeypatch.setenv("API_BASE_URL", "   ")

    result = agent.echo_environment_variable("API_BASE_URL")

    assert result == "[EMPTY NAMED VARIABLE]"
    assert output_path.read_text(encoding="utf-8") == "[EMPTY NAMED VARIABLE]"


def test_use_openai_responses_api_writes_output_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify the OpenAI workload saves and returns response text."""
    output_path = tmp_path / "alice.txt"
    expected_text = "Alice was beginning to get very tired."
    monkeypatch.setattr(agent, "_ALICE_OUTPUT_PATH", output_path)
    monkeypatch.setitem(
        __import__("sys").modules,
        "openai",
        SimpleNamespace(OpenAI=lambda: _FakeOpenAIClient(expected_text)),
    )

    result = agent.use_openai_responses_api()

    assert result == expected_text
    assert output_path.read_text(encoding="utf-8") == expected_text


def test_use_openai_agents_sdk_returns_final_output(monkeypatch) -> None:
    """Verify the Agents SDK workload returns the runner final output."""
    monkeypatch.setattr(
        agent,
        "create_html_explanation_agent",
        lambda model=agent._DEFAULT_MODEL: object(),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "agents",
        SimpleNamespace(Runner=_FakeRunner("Created example.html")),
    )

    result = agent.use_openai_agents_sdk()

    assert result == "Created example.html"


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self._content = content

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def read(self) -> bytes:
        return self._content.encode("utf-8")


class _FakeOpenAIClient:
    def __init__(self, content: str) -> None:
        self.responses = _FakeResponsesResource(content)


class _FakeResponsesResource:
    def __init__(self, content: str) -> None:
        self._content = content

    def create(self, **kwargs: object) -> object:
        return SimpleNamespace(output_text=self._content)


class _FakeRunner:
    def __init__(self, final_output: str) -> None:
        self._final_output = final_output

    def run_sync(self, *args: object, **kwargs: object) -> object:
        return SimpleNamespace(final_output=self._final_output)
