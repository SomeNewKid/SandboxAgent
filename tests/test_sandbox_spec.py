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
