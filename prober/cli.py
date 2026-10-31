import argparse
import asyncio
import sys
import time
from typing import Dict, Optional

from rich.console import Console
from rich.live import Live
from rich.table import Table

from .core.models import AdvertisementPacket, DeviceTelemetry
from .capture.ble_engine import BLECaptureEngine
from .dsp.kalman import RSSIStateFilter
from .dsp.path_loss import LogDistancePathLoss
from .dsp.sensing import RadioSensingDetector
from .storage.timeseries import TelemetryDatabase
from .ui.tui import TerminalDashboard


console = Console()


class ProberApplication:
    """Core application coordinator linking capture, DSP, storage, and UI."""

    def __init__(
        self,
        target_mac: Optional[str] = None,
        path_loss_n: float = 2.4,
        reference_tx_power: float = -59.0,
        db_path: Optional[str] = "telemetry.db",
        variance_threshold: float = 3.5,
    ):
        self.target_mac = target_mac.upper() if target_mac else None
        self.path_loss = LogDistancePathLoss(
            reference_tx_power=reference_tx_power,
            path_loss_exponent=path_loss_n,
        )
        self.db = TelemetryDatabase(db_path) if db_path else None

        # Per-device DSP state filters
        self.kalman_filters: Dict[str, RSSIStateFilter] = {}
        self.sensing_detectors: Dict[str, RadioSensingDetector] = {}
        self.variance_threshold = variance_threshold

        # Global telemetry store
        self.telemetry: Dict[str, DeviceTelemetry] = {}
        self.total_packets = 0

    def process_packet(self, packet: AdvertisementPacket) -> None:
        addr = packet.address
        self.total_packets += 1

        # Instantiate DSP filters for new device
        if addr not in self.kalman_filters:
            self.kalman_filters[addr] = RSSIStateFilter(initial_rssi=packet.rssi)
            self.sensing_detectors[addr] = RadioSensingDetector(
                variance_threshold_db2=self.variance_threshold
            )
            self.telemetry[addr] = DeviceTelemetry(address=addr, name=packet.name)

        # 1. Kalman Smoothing
        filtered_rssi = self.kalman_filters[addr].update(packet.rssi)

        # 2. Distance Estimation
        tx_pwr = float(packet.tx_power) if packet.tx_power is not None else None
        distance = self.path_loss.estimate_distance(filtered_rssi, tx_power=tx_pwr)

        # 3. Radio Sensing Perturbation Analysis
        variance, is_motion = self.sensing_detectors[addr].update(packet.rssi)

        # 4. Telemetry Update
        self.telemetry[addr].update(
            packet=packet,
            filtered_rssi=filtered_rssi,
            distance=distance,
            variance=variance,
            is_motion=is_motion,
        )

        # 5. Database Logging
        if self.db:
            try:
                self.db.record_packet(
                    packet=packet,
                    filtered_rssi=filtered_rssi,
                    distance=distance,
                    variance=variance,
                    is_motion=is_motion,
                )
            except Exception:
                pass


async def run_scan(args: argparse.Namespace) -> None:
    console.print(f"[bold cyan]Scanning BLE advertising packets for {args.duration}s...[/bold cyan]")
    app = ProberApplication(
        path_loss_n=args.n,
        reference_tx_power=args.tx_power,
        db_path=None,
    )

    engine = BLECaptureEngine(
        packet_callback=app.process_packet,
        min_rssi=args.min_rssi,
    )

    await engine.capture_stream(duration=args.duration)

    if not app.telemetry:
        console.print("[yellow]No BLE devices detected within the scan window.[/yellow]")
        return

    table = Table(
        title=f"Scan Summary: {len(app.telemetry)} Devices Discovered ({app.total_packets} Packets)",
        header_style="bold magenta",
        expand=True,
    )
    table.add_column("MAC Address", style="bold cyan")
    table.add_column("Name", style="white")
    table.add_column("Packets", justify="right")
    table.add_column("Avg RSSI", justify="right")
    table.add_column("Kalman RSSI", justify="right")
    table.add_column("Est. Distance", justify="right")
    table.add_column("Sensing Variance", justify="center")

    sorted_devs = sorted(app.telemetry.values(), key=lambda d: -d.packet_count)
    for dev in sorted_devs:
        table.add_row(
            dev.address,
            dev.name or "[dim]<Unknown>[/dim]",
            str(dev.packet_count),
            f"{dev.raw_rssi:.0f} dBm",
            f"{dev.filtered_rssi:.1f} dBm",
            f"{dev.estimated_distance:.2f} m",
            f"σ² = {dev.rssi_variance:.1f} dB²",
        )
    console.print(table)


async def run_monitor(args: argparse.Namespace) -> None:
    db_file = None if args.no_db else args.db
    app = ProberApplication(
        target_mac=args.target,
        path_loss_n=args.n,
        reference_tx_power=args.tx_power,
        db_path=db_file,
    )

    target_set = {args.target.upper()} if args.target else None
    engine = BLECaptureEngine(
        packet_callback=app.process_packet,
        target_macs=target_set,
    )

    dashboard = TerminalDashboard(target_mac=args.target)

    # Start capture engine in background
    capture_task = asyncio.create_task(engine.start())
    await asyncio.sleep(0.2)

    console.print("[bold green]Starting live telemetry monitor...[/bold green]")
    try:
        with Live(dashboard.render(app.telemetry, app.total_packets), refresh_per_second=4, console=console) as live:
            while True:
                live.update(dashboard.render(app.telemetry, app.total_packets))
                await asyncio.sleep(0.25)
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        await engine.stop()
        console.print("[yellow]Monitoring terminated cleanly.[/yellow]")


async def run_sense(args: argparse.Namespace) -> None:
    console.print("[bold yellow]Radio Sensing Mode: Environmental Motion & Channel Perturbation[/bold yellow]")
    console.print(f"Target filter: {args.target or 'Locking onto nearest / strongest beacon'}")

    app = ProberApplication(
        target_mac=args.target,
        variance_threshold=args.threshold,
        db_path=args.db,
    )

    target_addr = args.target.upper() if args.target else None
    locked_target: Optional[str] = target_addr

    def on_packet(pkt: AdvertisementPacket):
        nonlocal locked_target
        if locked_target is None:
            locked_target = pkt.address
            console.print(f"[bold green]Locked onto primary beacon:[/bold green] {locked_target} ({pkt.name or 'Unknown'})")

        if pkt.address == locked_target:
            app.process_packet(pkt)
            dev = app.telemetry[pkt.address]

            status = "[bold red on black]PERTURBATION DETECTED[/bold red on black]" if dev.is_motion_detected else "[green]CLEAR / STABLE[/green]"
            console.print(
                f"[dim]{time.strftime('%H:%M:%S')}[/dim] | "
                f"RSSI: [bold]{pkt.rssi:.0f} dBm[/bold] (Kalman: {dev.filtered_rssi:.1f}) | "
                f"Dist: {dev.estimated_distance:.2f} m | "
                f"Variance: [cyan]{dev.rssi_variance:.2f} dB²[/cyan] | "
                f"{status}"
            )

    engine = BLECaptureEngine(packet_callback=on_packet)
    await engine.start()
    try:
        while True:
            await asyncio.sleep(0.5)
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        await engine.stop()


def run_export(args: argparse.Namespace) -> None:
    db = TelemetryDatabase(args.db)
    count = db.export_csv(args.output)
    console.print(f"[bold green]Successfully exported {count} records to {args.output}[/bold green]")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="prober",
        description="Wireless Prober: BLE Advertising Monitor & Radio Sensing Platform",
    )
    subparsers = parser.add_subparsers(dest="command", help="Operational mode")

    # scan
    scan_p = subparsers.add_parser("scan", help="Quick discovery and distance overview")
    scan_p.add_argument("--duration", type=int, default=10, help="Scan duration in seconds (default: 10)")
    scan_p.add_argument("--min-rssi", type=float, default=-100.0, help="Minimum RSSI cutoff (default: -100)")
    scan_p.add_argument("--n", type=float, default=2.4, help="Path loss exponent (default: 2.4)")
    scan_p.add_argument("--tx-power", type=float, default=-59.0, help="Reference TxPower at 1m (default: -59.0)")

    # monitor
    mon_p = subparsers.add_parser("monitor", help="Live interactive terminal dashboard")
    mon_p.add_argument("--target", type=str, default=None, help="Filter by specific MAC address")
    mon_p.add_argument("--n", type=float, default=2.4, help="Path loss exponent (default: 2.4)")
    mon_p.add_argument("--tx-power", type=float, default=-59.0, help="Reference TxPower at 1m (default: -59.0)")
    mon_p.add_argument("--db", type=str, default="telemetry.db", help="SQLite database path")
    mon_p.add_argument("--no-db", action="store_true", help="Disable SQLite logging")

    # sense
    sense_p = subparsers.add_parser("sense", help="Real-time RF sensing & motion perturbation mode")
    sense_p.add_argument("--target", type=str, default=None, help="Target device MAC address")
    sense_p.add_argument("--threshold", type=float, default=3.5, help="Variance perturbation threshold (default: 3.5 dB²)")
    sense_p.add_argument("--db", type=str, default="telemetry.db", help="SQLite database path")

    # export
    exp_p = subparsers.add_parser("export", help="Export telemetry database to CSV")
    exp_p.add_argument("--db", type=str, default="telemetry.db", help="SQLite input database")
    exp_p.add_argument("--output", type=str, default="telemetry.csv", help="CSV destination file")

    args = parser.parse_args()

    if not args.command or args.command == "scan":
        asyncio.run(run_scan(args if args.command else argparse.Namespace(duration=10, min_rssi=-100.0, n=2.4, tx_power=-59.0)))
    elif args.command == "monitor":
        asyncio.run(run_monitor(args))
    elif args.command == "sense":
        asyncio.run(run_sense(args))
    elif args.command == "export":
        run_export(args)


if __name__ == "__main__":
    main()
