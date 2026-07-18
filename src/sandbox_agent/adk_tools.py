"""Google ADK adapters for Sandbox Agent tools."""

from __future__ import annotations

from google.adk.tools import FunctionTool

from .tools import capture_screenshot, save_html_document

save_html_document_tool = FunctionTool(save_html_document)
capture_screenshot_tool = FunctionTool(capture_screenshot)
