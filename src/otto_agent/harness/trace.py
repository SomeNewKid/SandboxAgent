"""Trace events recorded by the agent harness."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TraceEvent:
    """A structured event recorded during an agent run."""

    sender: str
    message: str


class Trace:
    """Collector for structured trace events."""

    def __init__(self) -> None:
        """Create an empty trace."""
        self._events: list[TraceEvent] = []

    @property
    def events(self) -> tuple[TraceEvent, ...]:
        """Return the recorded trace events."""
        return tuple(self._events)

    def event(self, sender: str, message: str) -> None:
        """Record a trace event."""
        self._events.append(TraceEvent(sender=sender, message=message))
