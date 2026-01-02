# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
CLI Integration for Dreaming Status.

Provides Rich console integration for displaying dreaming status updates
in the terminal.
"""

import threading
import time
from typing import Optional
from contextlib import contextmanager

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.spinner import Spinner
from rich.table import Table

from rra.status.dreaming import get_dreaming_status, StatusEntry, StatusType


class DreamingDisplay:
    """
    Rich console display for dreaming status.

    Shows a live-updating status line at the bottom of the terminal
    that displays what the system is currently doing.
    """

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize the dreaming display.

        Args:
            console: Rich Console instance (creates one if not provided)
        """
        self.console = console or Console()
        self._live: Optional[Live] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_status: Optional[str] = None

        # Register callback with dreaming status
        self._dreaming = get_dreaming_status()

    def _render_status(self) -> Panel:
        """Render the current status as a Rich Panel."""
        status = self._dreaming.current_status
        operation = self._dreaming.current_operation

        if not status:
            content = Text("Idle", style="dim")
        else:
            # Create styled text based on status type
            history = self._dreaming.get_history(1)
            if history:
                entry = history[0]
                if entry.status_type == StatusType.START:
                    content = Text()
                    content.append("", style="bold blue")
                    content.append(f" {status}", style="blue")
                elif entry.status_type == StatusType.COMPLETE:
                    content = Text()
                    content.append("", style="bold green")
                    content.append(f" {status}", style="green")
                elif entry.status_type == StatusType.ERROR:
                    content = Text()
                    content.append("", style="bold red")
                    content.append(f" {status}", style="red")
                else:
                    content = Text(status, style="cyan")
            else:
                content = Text(status, style="cyan")

        return Panel(
            content,
            title="[dim]Dreaming[/dim]",
            border_style="dim",
            padding=(0, 1),
        )

    def start(self) -> None:
        """Start the live dreaming display."""
        if self._running:
            return

        self._running = True
        self._live = Live(
            self._render_status(),
            console=self.console,
            refresh_per_second=0.2,  # 5 second refresh matches throttle
            transient=True,
        )
        self._live.start()

        # Start update thread
        self._thread = threading.Thread(target=self._update_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the live dreaming display."""
        self._running = False
        if self._live:
            self._live.stop()
            self._live = None
        if self._thread:
            self._thread.join(timeout=1)
            self._thread = None

    def _update_loop(self) -> None:
        """Update loop for the live display."""
        while self._running:
            if self._live:
                current_status = self._dreaming.current_status
                if current_status != self._last_status:
                    self._live.update(self._render_status())
                    self._last_status = current_status
            time.sleep(0.5)  # Check for updates every 500ms

    @contextmanager
    def live_display(self):
        """Context manager for live dreaming display."""
        self.start()
        try:
            yield self
        finally:
            self.stop()


def print_dreaming_status(console: Optional[Console] = None) -> None:
    """
    Print the current dreaming status once.

    Args:
        console: Rich Console instance (creates one if not provided)
    """
    console = console or Console()
    dreaming = get_dreaming_status()
    status = dreaming.current_status

    if status:
        console.print(f"[dim]Dreaming:[/dim] {status}")


def create_status_callback(console: Optional[Console] = None):
    """
    Create a callback that prints status updates to console.

    Args:
        console: Rich Console instance

    Returns:
        Callback function for dreaming status updates
    """
    console = console or Console()

    def callback(entry: StatusEntry) -> None:
        """Print status entry to console."""
        if entry.status_type == StatusType.START:
            console.print(f"[blue]Starting:[/blue] {entry.operation}")
        elif entry.status_type == StatusType.COMPLETE:
            if entry.duration_ms is not None:
                console.print(
                    f"[green]Completed:[/green] {entry.operation} "
                    f"[dim]({entry.duration_ms:.0f}ms)[/dim]"
                )
            else:
                console.print(f"[green]Completed:[/green] {entry.operation}")
        elif entry.status_type == StatusType.ERROR:
            console.print(f"[red]Error:[/red] {entry.operation} - {entry.details or 'Unknown'}")
        else:
            console.print(f"[cyan]{entry.operation}[/cyan]")

    return callback


def enable_dreaming_output(console: Optional[Console] = None) -> None:
    """
    Enable dreaming status output to console.

    Adds a callback to print all status updates to the console.

    Args:
        console: Rich Console instance
    """
    dreaming = get_dreaming_status()
    callback = create_status_callback(console)
    dreaming.add_callback(callback)


def get_dreaming_summary(console: Optional[Console] = None) -> Table:
    """
    Get a Rich table summarizing recent dreaming activity.

    Args:
        console: Rich Console instance

    Returns:
        Rich Table with recent status entries
    """
    dreaming = get_dreaming_status()
    history = dreaming.get_history(10)

    table = Table(title="Recent Activity", show_header=True)
    table.add_column("Time", style="dim", width=12)
    table.add_column("Status", width=10)
    table.add_column("Operation", style="cyan")
    table.add_column("Duration", justify="right", width=10)

    for entry in history:
        time_str = entry.timestamp.strftime("%H:%M:%S")

        if entry.status_type == StatusType.START:
            status = "[blue]START[/blue]"
        elif entry.status_type == StatusType.COMPLETE:
            status = "[green]DONE[/green]"
        elif entry.status_type == StatusType.ERROR:
            status = "[red]ERROR[/red]"
        else:
            status = "[dim]INFO[/dim]"

        duration = ""
        if entry.duration_ms is not None:
            if entry.duration_ms < 1000:
                duration = f"{entry.duration_ms:.0f}ms"
            else:
                duration = f"{entry.duration_ms / 1000:.1f}s"

        table.add_row(time_str, status, entry.operation, duration)

    return table
