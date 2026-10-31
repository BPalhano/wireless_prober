import time
from typing import Dict
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.console import Group

from ..core.models import DeviceTelemetry


class TerminalDashboard:
    """Live interactive terminal dashboard for BLE monitoring and radio sensing."""

    def __init__(self, target_mac: str = None):
        self.target_mac = target_mac.upper() if target_mac else None
        self.start_time = time.time()
        self.total_packets = 0

    def create_table(self, telemetry_map: Dict[str, DeviceTelemetry]) -> Table:
        table = Table(
            title="Active BLE Advertising Telemetry & Sensing Grid",
            border_style="cyan",
            header_style="bold white on dark_blue",
            expand=True,
        )

        table.add_column("MAC Address", style="bold cyan", no_wrap=True, width=18)
        table.add_column("Name", style="bright_white", width=20)
        table.add_column("Pkts", justify="right", width=6)
        table.add_column("Rate", justify="right", width=7)
        table.add_column("Raw RSSI", justify="right", width=9)
        table.add_column("Kalman RSSI", justify="right", width=12)
        table.add_column("Dist (m)", justify="right", width=9)
        table.add_column("RF Sensing State", justify="center", width=22)
        table.add_column("Age", justify="right", width=7)

        now = time.time()
        # Sort by most recently active, then by packet count
        sorted_devices = sorted(
            telemetry_map.values(),
            key=lambda d: (-d.last_seen, -d.packet_count),
        )

        for dev in sorted_devices:
            if self.target_mac and dev.address != self.target_mac:
                continue

            age_sec = max(0.0, now - dev.last_seen)
            age_str = f"{age_sec:.1f}s"

            # Color coding for distance
            if dev.estimated_distance < 1.5:
                dist_str = f"[bold green]{dev.estimated_distance:.2f} m[/bold green]"
            elif dev.estimated_distance < 4.0:
                dist_str = f"[yellow]{dev.estimated_distance:.2f} m[/yellow]"
            else:
                dist_str = f"[blue]{dev.estimated_distance:.2f} m[/blue]"

            # Color coding for RF sensing perturbation
            if dev.is_motion_detected:
                sensing_str = f"[bold red on black]PERTURBATION ({dev.rssi_variance:.1f})[/bold red on black]"
            else:
                sensing_str = f"[green]STABLE (σ²={dev.rssi_variance:.1f})[/green]"

            table.add_row(
                dev.address,
                dev.name[:18] if dev.name else "[dim]<Unknown>[/dim]",
                str(dev.packet_count),
                f"{dev.packet_rate:.1f}Hz",
                f"{dev.raw_rssi:.0f} dBm",
                f"[bold]{dev.filtered_rssi:.1f}[/bold] dBm",
                dist_str,
                sensing_str,
                age_str,
            )

        return table

    def render(self, telemetry_map: Dict[str, DeviceTelemetry], total_packets: int) -> Group:
        elapsed = time.time() - self.start_time
        device_count = len(telemetry_map)

        stats_text = Text()
        stats_text.append(f"Uptime: {elapsed:.1f}s | ", style="dim")
        stats_text.append(f"Devices Discovered: {device_count} | ", style="bold green")
        stats_text.append(f"Total Packets: {total_packets} | ", style="bold cyan")
        stats_text.append("Ctrl+C to stop", style="yellow")

        footer = Panel(stats_text, border_style="dim")
        table = self.create_table(telemetry_map)

        return Group(table, footer)
