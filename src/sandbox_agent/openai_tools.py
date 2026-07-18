"""OpenAI Agents SDK adapters for Sandbox Agent tools."""

from __future__ import annotations

from agents import function_tool

from .tools import capture_screenshot, save_html_document

save_html_document_tool = function_tool(save_html_document)
capture_screenshot_tool = function_tool(capture_screenshot)
