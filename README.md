# Sandbox Agent

Sandbox Agent is a small Python command-line sample for running an OpenAI
Agents SDK workflow inside a hardened Docker container. It generates a simple
HTML lesson page, serves it from inside the container, and uses Playwright and
Chromium to capture a screenshot.

> [!WARNING]
> This is an experimental project and should not be considered production-ready.

The project was created to carry forward the Docker sandbox harness from the
separate `SandboxTester` workbench without carrying forward the
`sandbox_tester` capability-probe engine. The sandbox harness starts a
disposable container, mounts a fresh run artifact directory, applies the
`no-shell-access` hardening profile, and runs `sandbox_agent` inside that
container.

## What It Does

The CLI is launched from the host, but the agent itself refuses to run unless it
detects the expected Docker sandbox environment:

```powershell
.\.venv\Scripts\python.exe -m sandbox_agent --profile no-shell-access
```

The Docker harness then:

- builds or reuses the `sandbox-agent/sandbox-agent` Docker image
- creates a timestamped run directory under `.docker_sandbox/runs`
- starts a disposable Linux container using the `no-shell-access` profile
- bind-mounts the run directory at `/sandbox-output`
- bind-mounts the current `src` tree at `/sandbox-source/src`
- forwards `OPENAI_API_KEY` into the container when it is present locally
- runs `sandbox_agent` through a Landlock path-policy launcher
- saves stdout, stderr, metadata, generated files, and screenshots as artifacts
- removes the disposable container by default

Inside the container, `sandbox_agent`:

1. Starts a local static HTTP server for `/sandbox-output/site`.
2. Creates an OpenAI Agents SDK agent named `HTML Lesson Page Builder`.
3. Gives the agent two tools:
   - save an HTML document into `/sandbox-output/site`
   - capture a screenshot of a served HTML document with Playwright
4. Asks the agent to create `index.html`, a basic lesson about HTML for a new
   developer at a middle-school reading level.
5. Saves a screenshot to `/sandbox-output/index.html.png`.

Direct execution without the Docker profile is intentionally blocked:

```powershell
.\.venv\Scripts\python.exe -m sandbox_agent
```

That command exits with a message telling the user to run through the Docker
sandbox.

## Requirements

- Python 3.11.
- PowerShell on Windows.
- Docker Desktop with Linux containers enabled.
- An `OPENAI_API_KEY` environment variable for OpenAI model calls.
- Network access to pull the Playwright Python Docker base image and the Squid
  gateway image the first time they are needed.

## Setup

Create the virtual environment and install the project with development
dependencies:

```powershell
.\scripts\setup-dev.ps1
```

The setup script expects Python 3.11 at the path configured in
`scripts\setup-dev.ps1`.

## Running

Run the sandboxed agent from the repository root:

```powershell
.\.venv\Scripts\python.exe -m sandbox_agent --profile no-shell-access
```

The command creates artifacts under a timestamped run directory:

```text
.docker_sandbox/runs/run-YYYY-mm-dd-HH-MM-SS/
  config.json
  gateway-logs.json
  gateway-start-results.json
  index.html.png
  landlock-policy.json
  run-metadata.json
  seccomp-profile.json
  site/
    index.html
  squid.conf
  stderr.txt
  stdout.txt
```

If the Dockerfile dependencies or image build settings change, remove the
existing image before running again so the harness rebuilds it:

```powershell
docker image rm sandbox-agent/sandbox-agent
```

## Docker Profile

This project keeps only one Docker profile from the original Sandbox Tester
lineage: `no-shell-access`.

The profile uses the image name `sandbox-agent/sandbox-agent` and applies a
defense-in-depth container policy that includes:

- a read-only root filesystem
- writable tmpfs mounts for `/tmp` and `/sandbox-work`
- a writable run artifact mount at `/sandbox-output`
- a read-only source mount at `/sandbox-source/src`
- a Landlock filesystem policy
- a seccomp profile denying privileged syscall families
- private IPC and cgroup namespaces
- dropped Linux capabilities and `no-new-privileges`
- CPU, memory, process, file descriptor, and file size limits
- an internal Docker network with a Squid egress gateway
- DNS and host-name controls for common host and metadata endpoints
- browser-surface hardening flags for Chromium
- removal or denial of common package-management, SSH, GPG, service-management,
  desktop-automation, and administration tools
- runtime guards for UDP sockets, all-interface binds, metadata endpoints, and
  hardware-device enumeration

The profile currently does not enable the Python-level
`SANDBOX_DENY_PROCESS_SPAWN` guard because the OpenAI Agents SDK imports code
that expects `subprocess.Popen` to remain class-like. Other process and shell
controls remain in place through image minimization, denied executable mounts,
seccomp, Landlock, and the read-only/noexec runtime layout.

## Architecture

The project is split into two packages:

- `sandbox_agent`: the AI agent runtime. It owns the OpenAI Agents SDK setup,
  the HTML generation prompt, the local static HTTP server, and the tools that
  write HTML and capture screenshots.
- `docker_sandbox`: the host/container harness extracted from Sandbox Tester.
  It owns Docker image creation, disposable container execution, hardening
  profile configuration, Landlock launching, environment forwarding, artifact
  persistence, and teardown.

The host-side command path is intentionally different from the in-container
agent path. `python -m sandbox_agent --profile no-shell-access` runs on the
host and delegates to `docker_sandbox`. Plain `python -m sandbox_agent` is the
in-container work path and requires both `SANDBOX_AGENT_CONTAINER=1` and the
expected mounted paths to exist.

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

## Project Structure

```text
src/sandbox_agent/
  __main__.py  Package entry point for python -m sandbox_agent
  cli.py       Host delegation and in-container agent entry point
  agent.py     OpenAI Agents SDK setup, prompt, and local HTTP server
  tools.py     Agent tools for saving HTML and capturing screenshots

src/docker_sandbox/
  __main__.py                   Package entry point for python -m docker_sandbox
  cli.py                        Docker sandbox command-line orchestration
  container_factory.py          Docker image inspection and build operations
  container_guard.py            Runtime guard for in-container execution
  landlock_runner.py            Linux Landlock path-policy launcher
  models.py                     Docker orchestration dataclasses
  profiles.py                   no-shell-access Docker hardening profile
  run_results.py                Local run artifact persistence
  sandbox_container.py          Disposable container execution and setup
  dockerfile/Dockerfile         Playwright Python image used for container runs
  dockerfile/runtime_sitecustomize.py
                                Python runtime guards for hardened images

tests/
  test_smoke.py
  test_tools.py

scripts/
  setup-dev.ps1
  check.ps1
```

## Notes

This project is a sandboxed-agent learning exercise, not a security proof. The
Docker profile is intended to reduce accidental host exposure and make the
runtime boundary explicit, but it should not be treated as a complete isolation
guarantee.

Agent behavior and final page content can vary between runs because the page is
model-generated. OpenAI API calls may incur usage costs.

The generated website and screenshot are run artifacts. They are written under
`.docker_sandbox/runs` and are ignored by Git.

## Third-Party Notices

This project has direct runtime dependencies on third-party Python packages,
including `openai-agents` (MIT), `playwright` (Apache-2.0), and `pillow`
(MIT-CMU). See each package's PyPI license metadata for full license and notice
terms.

## License

GNU General Public License v3.0. See the `LICENSE` file for details.
