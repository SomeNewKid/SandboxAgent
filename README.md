# Sandbox Agent

Sandbox Agent is a Python command-line project for running an OpenAI Agents SDK
workload inside a hardened, disposable Docker sandbox.

The current workload asks an agent to generate a small HTML lesson about the
basics of HTML, saves the generated page into the run output directory, serves
that page from inside the container, and uses Playwright with Chromium to
capture a screenshot.

> [!WARNING]
> This is an experimental sandboxing project and should not be treated as a
> finished security model.

## Current Workflow

Run the project from the repository root:

```powershell
.\.venv\Scripts\python.exe -m sandbox_agent
```

The host-side command loads `src/sandbox_agent/sandbox_spec.toml`, generates a
Dockerfile and low-level Docker profile from that spec, builds or reuses a
hash-tagged Docker image, starts a disposable container, and then runs
`sandbox_agent` inside the container.

Inside the container, Sandbox Agent:

1. Starts a local static HTTP server for `/sandbox-output/site`.
2. Creates an OpenAI Agents SDK agent named `HTML Lesson Page Builder`.
3. Gives the agent two tools:
   - save an HTML document into `/sandbox-output/site`
   - capture a screenshot of a served HTML document with Playwright/Chromium
4. Asks the agent to create `index.html`, a simple HTML lesson for a new
   developer.
5. Saves the screenshot as `/sandbox-output/index.html.png`.

Run artifacts are written under `.docker_sandbox/runs/run-*`.

## Sandbox Spec

The sandbox is driven by a declarative TOML file:

```toml
schema_version = 1
capabilities = [
  "network",
  "openai_agents",
  "playwright_chromium",
]
allowed_domains = []
allowed_ip_addresses = []
```

The design rule is that capabilities soften the sandbox only when necessary.
Unknown keys and unsupported capability values fail closed.

Supported capabilities:

- `network`: enables the Squid egress gateway. Network access is default-deny
  unless domains or IP addresses are allowed by the resolved profile.
- `openai`: installs the pinned OpenAI Python package, requires `network`, adds
  `.openai.com` to the resolved domain allowlist, and forwards
  `OPENAI_API_KEY` from the host.
- `openai_agents`: installs the pinned OpenAI Agents SDK package, requires
  `network`, adds `.openai.com`, forwards `OPENAI_API_KEY`, and sets
  `SANDBOX_DENY_PROCESS_SPAWN=0`.
- `playwright_chromium`: installs Playwright and Chromium, adds
  `/ms-playwright` to the Landlock allowlist, sets
  `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright`, allows process spawning, and
  increases browser-needed runtime limits.

`allowed_domains` and `allowed_ip_addresses` refine the `network` capability.
They do not enable networking by themselves.

Environment variables can be declared explicitly:

```toml
[[environment_variables]]
name = "API_BASE_URL"
value = "https://example.com"
```

Or copied from the host:

```toml
[[environment_variables]]
name = "OPENAI_API_KEY"
from_host = true
```

OpenAI capabilities add `OPENAI_API_KEY` automatically, so the current spec does
not need to declare it manually.

## Docker Image Generation

Docker images are tagged from the normalized sandbox spec:

```text
sandbox-agent/sandbox-agent:<schema-version>-<spec-hash>
```

For example:

```text
sandbox-agent/sandbox-agent:1-7ab18e84292c35c2
```

The generated Dockerfile is written both to the build area and to each run
directory as an artifact. The resolved low-level profile is also written to the
run directory as `resolved-profile.json`.

If the spec changes, the hash changes and a new image tag is used. If the
generator logic changes without the spec changing, bump the schema version to
force a new image.

## Run Artifacts

A successful run directory contains files similar to:

```text
.docker_sandbox/runs/run-YYYY-mm-dd-HH-MM-SS/
  Dockerfile
  config.json
  gateway-logs.json
  gateway-start-results.json
  index.html.png
  landlock-policy.json
  resolved-profile.json
  run-metadata.json
  sandbox-spec.json
  seccomp-profile.json
  site/
    index.html
  squid.conf
  stderr.txt
  stdout.txt
```

`stdout.txt` contains the agent's final message. `stderr.txt` should normally be
empty.

## Requirements

- Python 3.11.
- PowerShell on Windows.
- Docker Desktop with Linux containers enabled.
- `OPENAI_API_KEY` in the host environment.
- Network access during image builds to download Python packages, Linux
  packages, and Playwright browser binaries.
- Network access during runs to OpenAI API endpoints through the Squid gateway.

## Setup

Create the virtual environment and install development dependencies:

```powershell
.\scripts\setup-dev.ps1
```

## Development Checks

Run formatting, linting, type checking, and tests:

```powershell
.\scripts\check.ps1
```

This runs:

- `ruff format .`
- `ruff check .`
- `pyright`
- `pytest`

## Architecture

The project has two main packages:

- `sandbox_agent`: the in-container workload. It owns the OpenAI Agents SDK
  setup, the HTML lesson prompt, the local HTTP server, and the tools for saving
  HTML and capturing screenshots.
- `docker_sandbox`: the host/container harness extracted from the sibling
  SandboxTester workbench. It owns sandbox spec loading, Dockerfile generation,
  profile resolution, image creation, disposable container execution, Landlock
  launching, egress gateway setup, artifact persistence, and teardown.

The command path deliberately differs by location:

- On the host, `python -m sandbox_agent` delegates to `docker_sandbox`.
- Inside the container, `python -m sandbox_agent` runs the workload.

The in-container path is guarded by `SANDBOX_AGENT_CONTAINER=1` and expected
mounts such as `/sandbox-output`, `/sandbox-work`, and `/sandbox-source/src`.

## Project Structure

```text
src/sandbox_agent/
  __main__.py        Package entry point for python -m sandbox_agent
  agent.py           OpenAI Agents SDK workload and local HTTP server
  cli.py             Host delegation and in-container workload entry point
  sandbox_spec.toml  Declarative sandbox capability spec
  tools.py           Agent tools for saving HTML and capturing screenshots

src/docker_sandbox/
  __main__.py                         Package entry point for docker_sandbox
  cli.py                              Docker sandbox command-line orchestration
  container_factory.py                Docker image inspection and build
  container_guard.py                  Runtime guard for in-container execution
  landlock_runner.py                  Linux Landlock path-policy launcher
  models.py                           Docker orchestration dataclasses
  profiles.py                         Legacy named profile definitions
  run_results.py                      Local run artifact persistence
  sandbox_container.py                Disposable container execution and setup
  sandbox_spec.py                     Spec validation and profile/Dockerfile generation
  dockerfile/remove_python_packaging.py
  dockerfile/runtime_sitecustomize.py

tests/
  test_sandbox_spec.py
  test_smoke.py
  test_tools.py
```

## Notes

Sandbox Agent is a learning and hardening exercise, not a security proof. The
container policy reduces accidental host exposure and makes required capability
softening visible, but Docker, Landlock, seccomp, Squid, and Python runtime
guards should not be interpreted as a complete isolation guarantee.

Generated content can vary between runs because it is model-generated. OpenAI
API calls may incur usage costs.

Run artifacts under `.docker_sandbox/runs` are ignored by Git.

## Third-Party Notices

This project uses third-party packages including `openai-agents`, `openai`,
`playwright`, and `pillow`. See each package's license metadata for details.

## License

GNU General Public License v3.0. See the `LICENSE` file for details.
