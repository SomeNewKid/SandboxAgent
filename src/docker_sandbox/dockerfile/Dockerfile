FROM mcr.microsoft.com/playwright/python:v1.61.0-noble

ARG SANDBOX_MINIMIZE_IMAGE=false
ARG SANDBOX_REMOVE_PYTHON_PACKAGING=false
ARG SANDBOX_REMOVE_DESKTOP_AUTOMATION=false
ARG SANDBOX_REMOVE_PACKAGE_METADATA=false

WORKDIR /opt/sandbox-agent

RUN apt-get update \
    && apt-get install --yes --no-install-recommends python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash sandbox

RUN python -m venv /opt/sandbox-agent/.venv

ENV PATH="/opt/sandbox-agent/.venv/bin:${PATH}"

COPY pyproject.toml README.md ./
COPY ["src/docker_sandbox/dockerfile/runtime_sitecustomize.py", "/tmp/runtime_sitecustomize.py"]

RUN pip install --no-cache-dir openai-agents pillow playwright

RUN if [ "${SANDBOX_MINIMIZE_IMAGE}" = "true" ]; then \
        apt-get update \
        && apt-get purge --yes --auto-remove \
            git \
            gnupg \
            gpg \
            gpg-agent \
            openssh-client \
            perl \
        || true; \
        rm -f \
            /opt/sandbox-agent/.venv/bin/pip \
            /opt/sandbox-agent/.venv/bin/pip3 \
            /usr/bin/apt \
            /usr/bin/apt-get \
            /usr/bin/bash \
            /usr/bin/busctl \
            /usr/bin/dbus-send \
            /usr/bin/dpkg \
            /usr/bin/dpkg-query \
            /usr/bin/findmnt \
            /usr/bin/git \
            /usr/bin/gpg \
            /usr/bin/gpg-connect-agent \
            /usr/bin/gpgconf \
            /usr/bin/journalctl \
            /usr/bin/loginctl \
            /usr/bin/mount \
            /usr/bin/nice \
            /usr/bin/nohup \
            /usr/bin/nsenter \
            /usr/bin/perl \
            /usr/bin/renice \
            /usr/bin/scp \
            /usr/bin/sftp \
            /usr/bin/setsid \
            /usr/bin/ssh \
            /usr/bin/ssh-add \
            /usr/bin/su \
            /usr/bin/systemd-run \
            /usr/bin/systemctl \
            /usr/bin/umount \
            /usr/bin/unshare \
            /usr/sbin/service; \
        rm -rf /var/lib/apt/lists/* /var/cache/apt/*; \
    fi

RUN if [ "${SANDBOX_REMOVE_PYTHON_PACKAGING}" = "true" ]; then \
        python -c "import pathlib, shutil, sysconfig; paths = {pathlib.Path(sysconfig.get_path(name)) for name in ('purelib', 'platlib', 'stdlib')}; paths.update(path for root in (pathlib.Path('/usr/local/lib'), pathlib.Path('/usr/lib')) if root.exists() for pattern in ('python*/dist-packages', 'python*/site-packages', 'python*/ensurepip') for path in root.glob(pattern)); names = ('_distutils_hack', 'ensurepip', 'pip', 'pkg_resources', 'setuptools', 'wheel'); patterns = [*names, *(f'{name}-*.dist-info' for name in names), *(f'{name}-*.egg-info' for name in names), 'distutils-precedence.pth']; [shutil.rmtree(match, ignore_errors=True) if match.is_dir() else match.unlink(missing_ok=True) for path in paths for pattern in patterns for match in path.glob(pattern)]; [shutil.copyfile('/tmp/runtime_sitecustomize.py', path / 'sitecustomize.py') for path in paths if path.exists() and path.name != 'ensurepip']" \
        && rm -f \
            /opt/sandbox-agent/.venv/bin/pip \
            /opt/sandbox-agent/.venv/bin/pip3 \
            /opt/sandbox-agent/.venv/bin/pip3.* \
            /opt/sandbox-agent/.venv/bin/wheel \
            /usr/local/bin/pip \
            /usr/local/bin/pip3 \
            /usr/local/bin/pip3.* \
            /usr/local/bin/wheel \
            /usr/bin/pip \
            /usr/bin/pip3 \
            /usr/bin/pip3.* \
            /usr/bin/wheel; \
    fi

RUN if [ "${SANDBOX_REMOVE_DESKTOP_AUTOMATION}" = "true" ]; then \
        rm -f \
            /usr/bin/busctl \
            /usr/bin/dbus-send \
            /usr/bin/gdbus \
            /usr/bin/qdbus \
            /usr/bin/wmctrl \
            /usr/bin/xdotool; \
    fi

RUN if [ "${SANDBOX_REMOVE_PACKAGE_METADATA}" = "true" ]; then \
        rm -rf \
            /var/cache/apt \
            /var/lib/apt \
            /var/lib/dpkg \
            /var/log/apt; \
    fi
