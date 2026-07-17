"""Tests for Sandbox Agent tools."""

from pathlib import Path

from sandbox_agent import tools


def test_save_html_document_creates_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify the HTML tool writes into the configured site directory."""
    output_directory = tmp_path / "sandbox-output"
    monkeypatch.setattr(tools, "_OUTPUT_DIRECTORY", output_directory)
    monkeypatch.setattr(tools, "_SITE_DIRECTORY", output_directory / "site")

    result = tools.save_html_document("index.html", "<h1>Hello</h1>")

    assert result == {
        "success": True,
        "message": "Created index.html",
    }
    assert (output_directory / "site" / "index.html").read_text(
        encoding="utf-8"
    ) == "<h1>Hello</h1>"


def test_save_html_document_rejects_parent_traversal(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify the HTML tool does not write outside the site directory."""
    output_directory = tmp_path / "sandbox-output"
    monkeypatch.setattr(tools, "_OUTPUT_DIRECTORY", output_directory)
    monkeypatch.setattr(tools, "_SITE_DIRECTORY", output_directory / "site")

    result = tools.save_html_document("../escape.html", "<h1>Hello</h1>")

    assert result == {
        "success": False,
        "message": "Failed to create `../escape.html",
    }
    assert not (output_directory / "escape.html").exists()


def test_build_document_url_quotes_file_name(monkeypatch) -> None:
    """Verify screenshot URLs are built from the configured HTTP origin."""
    monkeypatch.setenv("SANDBOX_AGENT_HTTP_BASE_URL", "http://127.0.0.1:12345/")

    url = tools._build_document_url("pages/hello world.html")

    assert url == "http://127.0.0.1:12345/pages/hello%20world.html"
