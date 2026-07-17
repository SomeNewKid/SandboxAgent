"""Tools used by the Sandbox Agent."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

from agents import function_tool

_OUTPUT_DIRECTORY = Path("/sandbox-output")
_SITE_DIRECTORY = _OUTPUT_DIRECTORY / "site"
_HTTP_BASE_URL_ENVIRONMENT_VARIABLE = "SANDBOX_AGENT_HTTP_BASE_URL"
_DEFAULT_HTTP_BASE_URL = "http://127.0.0.1:8000"


def save_html_document(file_name: str, file_contents: str) -> dict[str, bool | str]:
    """Save an HTML document into the sandbox web root."""
    try:
        file_path = _resolve_site_path(file_name)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(file_contents, encoding="utf-8")
    except OSError:
        return _failure("create", file_name)

    if not file_path.exists():
        return _failure("create", file_name)

    return {
        "success": True,
        "message": f"Created {file_name}",
    }


def capture_screenshot(file_name: str) -> dict[str, bool | str]:
    """Capture a screenshot of a file served by the sandbox HTTP server."""
    from playwright.sync_api import sync_playwright

    try:
        screenshot_path = _resolve_screenshot_path(file_name)
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        url = _build_document_url(file_name)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                args=(
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                )
            )
            try:
                page = browser.new_page(viewport={"width": 1280, "height": 720})
                page.goto(url, wait_until="networkidle")
                page.screenshot(path=str(screenshot_path), full_page=True)
            finally:
                browser.close()
    except Exception:
        return _failure("capture", file_name)

    if not screenshot_path.exists():
        return _failure("capture", file_name)

    return {
        "success": True,
        "message": f"Captured {file_name}",
    }


def _resolve_site_path(file_name: str) -> Path:
    return _resolve_child_path(_SITE_DIRECTORY, file_name)


def _resolve_screenshot_path(file_name: str) -> Path:
    return _resolve_child_path(_OUTPUT_DIRECTORY, f"{file_name}.png")


def _resolve_child_path(parent: Path, child_name: str) -> Path:
    child_path = parent / child_name
    resolved_parent = parent.resolve(strict=False)
    resolved_child = child_path.resolve(strict=False)
    if not _is_relative_to(resolved_child, resolved_parent):
        raise OSError(f"Refusing to write outside {resolved_parent}: {child_name}")

    return resolved_child


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False

    return True


def _build_document_url(file_name: str) -> str:
    base_url = os.environ.get(
        _HTTP_BASE_URL_ENVIRONMENT_VARIABLE,
        _DEFAULT_HTTP_BASE_URL,
    ).rstrip("/")
    quoted_file_name = quote(file_name.replace("\\", "/"), safe="/")
    return f"{base_url}/{quoted_file_name}"


def _failure(action: str, file_name: str) -> dict[str, bool | str]:
    return {
        "success": False,
        "message": f"Failed to {action} `{file_name}",
    }


save_html_document_tool = function_tool(save_html_document)
capture_screenshot_tool = function_tool(capture_screenshot)
