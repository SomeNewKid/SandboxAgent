"""Tests for declarative sandbox specifications."""

from __future__ import annotations

from pathlib import Path

import pytest

from docker_sandbox.sandbox_container import _build_allowed_gateway_domains
from docker_sandbox.sandbox_spec import (
    generate_dockerfile,
    load_sandbox_spec,
    resolve_environment_variables,
    resolve_local_environment_variable_names,
    resolve_profile,
)


def test_network_capability_resolves_gateway_profile(tmp_path: Path) -> None:
    """Verify network specs enable the gateway and remove Docker network none."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network"]',
                'allowed_domains = [".example.com"]',
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    profile = resolve_profile(load_sandbox_spec(spec_path))

    assert profile.network_gateway is not None
    assert profile.network_gateway.allowed_domains == (".example.com",)
    assert "127.0.0.1" in profile.network_gateway.no_proxy_hosts
    assert "localhost" in profile.network_gateway.no_proxy_hosts
    assert "--network" not in profile.container_run_options
    assert "none" not in profile.container_run_options


def test_allowlists_require_network_capability(tmp_path: Path) -> None:
    """Verify allowlists cannot silently enable network access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                "capabilities = []",
                'allowed_domains = [".example.com"]',
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="require the network capability"):
        load_sandbox_spec(spec_path)


def test_gateway_domains_use_only_configured_allowlist() -> None:
    """Verify legacy fixture metadata does not widen the network allowlist."""
    domains = _build_allowed_gateway_domains(
        (".example.com",),
        {
            "allowed_domain": "ignored.test",
            "git_remote_url": "https://github.com/example/project.git",
        },
    )

    assert domains == (".example.com",)


def test_environment_variables_support_explicit_and_host_values(
    tmp_path: Path,
) -> None:
    """Verify environment variables support explicit and host-sourced values."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                "capabilities = []",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
                "",
                "[[environment_variables]]",
                'name = "API_BASE_URL"',
                'value = "https://example.com"',
                "",
                "[[environment_variables]]",
                'name = "OPENAI_API_KEY"',
                "from_host = true",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)

    assert resolve_environment_variables(spec) == (
        ("API_BASE_URL", "https://example.com"),
        ("OPENAI_API_KEY", "[local]"),
    )
    assert resolve_local_environment_variable_names(spec) == frozenset(
        {"OPENAI_API_KEY"}
    )


def test_environment_variables_require_exactly_one_value_source(
    tmp_path: Path,
) -> None:
    """Verify environment variable entries fail closed when ambiguous."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                "capabilities = []",
                "allowed_domains = []",
                "allowed_ip_addresses = []",
                "",
                "[[environment_variables]]",
                'name = "API_BASE_URL"',
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="exactly one"):
        load_sandbox_spec(spec_path)


def test_openai_capability_requires_network(tmp_path: Path) -> None:
    """Verify OpenAI cannot silently enable network access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["openai"]',
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires the network capability"):
        load_sandbox_spec(spec_path)


def test_openai_agents_capability_requires_network(tmp_path: Path) -> None:
    """Verify OpenAI Agents cannot silently enable network access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["openai_agents"]',
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires the network capability"):
        load_sandbox_spec(spec_path)


def test_anthropic_python_capability_requires_network(tmp_path: Path) -> None:
    """Verify Anthropic Python SDK cannot silently enable network access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["anthropic_python"]',
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires the network capability"):
        load_sandbox_spec(spec_path)


def test_anthropic_claude_capability_requires_network(tmp_path: Path) -> None:
    """Verify Claude Agent SDK cannot silently enable network access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["anthropic_claude"]',
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires the network capability"):
        load_sandbox_spec(spec_path)


def test_beeai_capability_requires_network(tmp_path: Path) -> None:
    """Verify BeeAI cannot silently enable network access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["ibm_beeai"]',
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires the network capability"):
        load_sandbox_spec(spec_path)


def test_google_adk_capability_requires_network(tmp_path: Path) -> None:
    """Verify Google ADK cannot silently enable network access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["google_adk"]',
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires the network capability"):
        load_sandbox_spec(spec_path)


def test_langchain_capability_requires_network(tmp_path: Path) -> None:
    """Verify LangChain cannot silently enable network access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["langchain"]',
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires the network capability"):
        load_sandbox_spec(spec_path)


def test_langgraph_capability_requires_network(tmp_path: Path) -> None:
    """Verify LangGraph cannot silently enable network access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["langgraph"]',
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires the network capability"):
        load_sandbox_spec(spec_path)


def test_microsoft_agent_capability_requires_network(tmp_path: Path) -> None:
    """Verify Microsoft Agent Framework cannot silently enable network access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["microsoft_agent"]',
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires the network capability"):
        load_sandbox_spec(spec_path)


def test_crewai_capability_requires_network(tmp_path: Path) -> None:
    """Verify CrewAI cannot silently enable network access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["crewai"]',
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires the network capability"):
        load_sandbox_spec(spec_path)


def test_otto_agent_capability_requires_network(tmp_path: Path) -> None:
    """Verify Otto Agent cannot silently enable network access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["otto_agent"]',
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires the network capability"):
        load_sandbox_spec(spec_path)


def test_openai_capability_resolves_required_runtime_support(
    tmp_path: Path,
) -> None:
    """Verify OpenAI adds only its needed package, domain, and host API key."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "openai"]',
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)
    profile = resolve_profile(spec)

    assert profile.network_gateway is not None
    assert profile.network_gateway.allowed_domains == (".openai.com",)
    assert resolve_environment_variables(spec) == (("OPENAI_API_KEY", "[local]"),)
    assert resolve_local_environment_variable_names(spec) == frozenset(
        {"OPENAI_API_KEY"}
    )
    assert all(policy.name != "OPENAI_API_KEY" for policy in profile.environment)
    assert "openai==2.45.0" in generate_dockerfile(spec)


def test_openai_agents_capability_resolves_required_runtime_support(
    tmp_path: Path,
) -> None:
    """Verify OpenAI Agents adds its package without broad shell access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "openai_agents"]',
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)
    profile = resolve_profile(spec)

    assert profile.network_gateway is not None
    assert profile.network_gateway.allowed_domains == (".openai.com",)
    assert resolve_environment_variables(spec) == (("OPENAI_API_KEY", "[local]"),)
    assert all(policy.name != "OPENAI_API_KEY" for policy in profile.environment)
    assert any(
        policy.name == "SANDBOX_DENY_PROCESS_SPAWN" and policy.value == "1"
        for policy in profile.environment
    )
    dockerfile = generate_dockerfile(spec)
    assert "openai-agents==0.18.2" in dockerfile
    assert "openai==2.45.0" not in dockerfile


def test_anthropic_python_capability_resolves_required_runtime_support(
    tmp_path: Path,
) -> None:
    """Verify Anthropic Python SDK adds its package, domain, and host API key."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "anthropic_python"]',
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)
    profile = resolve_profile(spec)

    assert profile.network_gateway is not None
    assert profile.network_gateway.allowed_domains == (".anthropic.com",)
    assert resolve_environment_variables(spec) == (("ANTHROPIC_API_KEY", "[local]"),)
    assert resolve_local_environment_variable_names(spec) == frozenset(
        {"ANTHROPIC_API_KEY"}
    )
    assert all(policy.name != "ANTHROPIC_API_KEY" for policy in profile.environment)
    dockerfile = generate_dockerfile(spec)
    assert "anthropic==0.116.0" in dockerfile
    assert "openai==2.45.0" not in dockerfile
    assert "openai-agents==0.18.2" not in dockerfile


def test_anthropic_claude_capability_resolves_required_runtime_support(
    tmp_path: Path,
) -> None:
    """Verify Claude Agent SDK adds its package, domain, and host API key."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "anthropic_claude"]',
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)
    profile = resolve_profile(spec)

    assert profile.network_gateway is not None
    assert profile.network_gateway.allowed_domains == (".anthropic.com",)
    assert resolve_environment_variables(spec) == (("ANTHROPIC_API_KEY", "[local]"),)
    assert resolve_local_environment_variable_names(spec) == frozenset(
        {"ANTHROPIC_API_KEY"}
    )
    assert all(policy.name != "ANTHROPIC_API_KEY" for policy in profile.environment)
    assert any(
        policy.name == "SANDBOX_DENY_PROCESS_SPAWN" and policy.value == "0"
        for policy in profile.environment
    )
    dockerfile = generate_dockerfile(spec)
    assert "claude-agent-sdk==0.2.120" in dockerfile
    assert "anthropic==0.116.0" not in dockerfile
    assert "openai-agents==0.18.2" not in dockerfile


def test_beeai_capability_resolves_required_runtime_support(
    tmp_path: Path,
) -> None:
    """Verify BeeAI adds its package, OpenAI domain, and host API key."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "ibm_beeai"]',
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)
    profile = resolve_profile(spec)

    assert profile.network_gateway is not None
    assert profile.network_gateway.allowed_domains == (".openai.com",)
    assert resolve_environment_variables(spec) == (("OPENAI_API_KEY", "[local]"),)
    assert all(policy.name != "OPENAI_API_KEY" for policy in profile.environment)
    dockerfile = generate_dockerfile(spec)
    assert "beeai-framework==0.1.81" in dockerfile
    assert "'litellm[proxy]==1.92.0'" in dockerfile
    assert "openai-agents==0.18.2" not in dockerfile


def test_google_adk_capability_resolves_required_runtime_support(
    tmp_path: Path,
) -> None:
    """Verify Google ADK adds its package, OpenAI domain, and host API key."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "google_adk"]',
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)
    profile = resolve_profile(spec)

    assert profile.network_gateway is not None
    assert profile.network_gateway.allowed_domains == (".openai.com",)
    assert resolve_environment_variables(spec) == (("OPENAI_API_KEY", "[local]"),)
    assert all(policy.name != "OPENAI_API_KEY" for policy in profile.environment)
    dockerfile = generate_dockerfile(spec)
    assert "google-adk==2.5.0" in dockerfile
    assert "'litellm[proxy]==1.92.0'" in dockerfile
    assert "openai-agents==0.18.2" not in dockerfile


def test_langchain_capability_resolves_required_runtime_support(
    tmp_path: Path,
) -> None:
    """Verify LangChain adds its packages, OpenAI domain, and host API key."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "langchain"]',
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)
    profile = resolve_profile(spec)

    assert profile.network_gateway is not None
    assert profile.network_gateway.allowed_domains == (".openai.com",)
    assert resolve_environment_variables(spec) == (("OPENAI_API_KEY", "[local]"),)
    assert all(policy.name != "OPENAI_API_KEY" for policy in profile.environment)
    dockerfile = generate_dockerfile(spec)
    assert "langchain==1.3.14" in dockerfile
    assert "langchain-openai==1.3.5" in dockerfile
    assert "openai-agents==0.18.2" not in dockerfile


def test_langgraph_capability_resolves_required_runtime_support(
    tmp_path: Path,
) -> None:
    """Verify LangGraph adds its packages, OpenAI domain, and host API key."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "langgraph"]',
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)
    profile = resolve_profile(spec)

    assert profile.network_gateway is not None
    assert profile.network_gateway.allowed_domains == (".openai.com",)
    assert resolve_environment_variables(spec) == (("OPENAI_API_KEY", "[local]"),)
    assert all(policy.name != "OPENAI_API_KEY" for policy in profile.environment)
    dockerfile = generate_dockerfile(spec)
    assert "langgraph==1.2.9" in dockerfile
    assert "langchain-openai==1.3.5" in dockerfile
    assert "langchain==1.3.14" not in dockerfile
    assert "openai-agents==0.18.2" not in dockerfile


def test_microsoft_agent_capability_resolves_required_runtime_support(
    tmp_path: Path,
) -> None:
    """Verify Microsoft Agent Framework adds its package and OpenAI support."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "microsoft_agent"]',
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)
    profile = resolve_profile(spec)

    assert profile.network_gateway is not None
    assert profile.network_gateway.allowed_domains == (".openai.com",)
    assert resolve_environment_variables(spec) == (("OPENAI_API_KEY", "[local]"),)
    assert all(policy.name != "OPENAI_API_KEY" for policy in profile.environment)
    assert any(
        policy.name == "SANDBOX_DENY_PROCESS_SPAWN" and policy.value == "1"
        for policy in profile.environment
    )
    dockerfile = generate_dockerfile(spec)
    assert "agent-framework==1.11.0" in dockerfile
    assert "openai-agents==0.18.2" not in dockerfile


def test_crewai_capability_resolves_required_runtime_support(
    tmp_path: Path,
) -> None:
    """Verify CrewAI adds its package and OpenAI support."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "crewai"]',
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)
    profile = resolve_profile(spec)

    assert profile.network_gateway is not None
    assert profile.network_gateway.allowed_domains == (".openai.com",)
    assert resolve_environment_variables(spec) == (("OPENAI_API_KEY", "[local]"),)
    assert all(policy.name != "OPENAI_API_KEY" for policy in profile.environment)
    assert any(
        policy.name == "SANDBOX_DENY_PROCESS_SPAWN" and policy.value == "1"
        for policy in profile.environment
    )
    assert any(
        policy.name == "CREWAI_TRACING_ENABLED" and policy.value == "false"
        for policy in profile.environment
    )
    assert any(
        policy.name == "OTEL_SDK_DISABLED" and policy.value == "true"
        for policy in profile.environment
    )
    assert (
        "/tmp/sandbox-home:rw,nosuid,nodev,noexec,size=64m,uid=1000,gid=1000,mode=700"
        in profile.container_run_options
    )
    dockerfile = generate_dockerfile(spec)
    assert "crewai==1.15.3" in dockerfile
    assert "openai-agents==0.18.2" not in dockerfile


def test_otto_agent_capability_resolves_required_runtime_support(
    tmp_path: Path,
) -> None:
    """Verify Otto Agent adds only OpenAI runtime support."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["network", "otto_agent"]',
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)
    profile = resolve_profile(spec)

    assert profile.network_gateway is not None
    assert profile.network_gateway.allowed_domains == (".openai.com",)
    assert resolve_environment_variables(spec) == (("OPENAI_API_KEY", "[local]"),)
    assert resolve_local_environment_variable_names(spec) == frozenset(
        {"OPENAI_API_KEY"}
    )
    assert all(policy.name != "OPENAI_API_KEY" for policy in profile.environment)
    assert any(
        policy.name == "SANDBOX_DENY_PROCESS_SPAWN" and policy.value == "1"
        for policy in profile.environment
    )
    dockerfile = generate_dockerfile(spec)
    assert "openai==2.45.0" in dockerfile
    assert "openai-agents==0.18.2" not in dockerfile
    assert "crewai==1.15.3" not in dockerfile


def test_playwright_chromium_capability_resolves_browser_runtime_support(
    tmp_path: Path,
) -> None:
    """Verify Playwright adds Chromium packages without broad shell access."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["playwright_chromium"]',
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    spec = load_sandbox_spec(spec_path)
    profile = resolve_profile(spec)
    dockerfile = generate_dockerfile(spec)

    assert profile.network_gateway is None
    assert profile.browser_surface is not None
    assert "playwright==1.61.0" in dockerfile
    assert "python -m playwright install --with-deps chromium" in dockerfile
    assert any(rule.path == "/ms-playwright" for rule in profile.landlock_rules)
    assert profile.pids_limit == 512
    assert profile.memory == "2g"
    assert profile.shm_size == "1g"
    assert any(
        ulimit.name == "fsize" and ulimit.soft == 52428800 for ulimit in profile.ulimits
    )
    assert any(
        policy.name == "SANDBOX_DENY_PROCESS_SPAWN" and policy.value == "1"
        for policy in profile.environment
    )


def test_shell_access_capability_allows_process_spawn(tmp_path: Path) -> None:
    """Verify shell access is an explicit capability."""
    spec_path = tmp_path / "sandbox_spec.toml"
    spec_path.write_text(
        "\n".join(
            [
                "schema_version = 1",
                'capabilities = ["shell_access"]',
                "allowed_domains = []",
                "allowed_ip_addresses = []",
            ]
        ),
        encoding="utf-8",
    )

    profile = resolve_profile(load_sandbox_spec(spec_path))

    assert any(
        policy.name == "SANDBOX_DENY_PROCESS_SPAWN" and policy.value == "0"
        for policy in profile.environment
    )
