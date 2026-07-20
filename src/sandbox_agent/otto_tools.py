"""Otto Agent adapters for Sandbox Agent tools."""

from __future__ import annotations

from otto_agent.function_tool import FunctionTool
from otto_agent.tool import ToolArgument

from .tools import capture_screenshot, save_html_document

save_html_document_tool = FunctionTool(
    name="save_html_document",
    description="Save an HTML document into the sandbox web root.",
    function=save_html_document,
    arguments=(
        ToolArgument(
            name="file_name",
            argument_type="string",
            description="The name of the HTML file to save.",
        ),
        ToolArgument(
            name="file_contents",
            argument_type="string",
            description="The complete HTML document contents.",
        ),
    ),
    result_key="result",
)

capture_screenshot_tool = FunctionTool(
    name="capture_screenshot",
    description="Capture a screenshot of a file served by the sandbox HTTP server.",
    function=capture_screenshot,
    arguments=(
        ToolArgument(
            name="file_name",
            argument_type="string",
            description="The name of the served HTML file to screenshot.",
        ),
    ),
    result_key="result",
)
