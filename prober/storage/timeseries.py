import sqlite3
import csv
from pathlib import Path
from typing import Optional, List, Dict, Any
from ..core.models import AdvertisementPacket


class TelemetryDatabase:
    """Lightweight SQLite database for storing BLE telemetry and RF sensing logs."""

    def __init__(self, db_path: str = "telemetry.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS packets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    address TEXT NOT NULL,
                    name TEXT,
                    rssi REAL NOT NULL,
                    filtered_rssi REAL,
                    tx_power INTEGER,
                    distance REAL,
                    variance REAL,
                    is_motion INTEGER
                );
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_packets_addr_time
                ON packets (address, timestamp);
                """
            )
            conn.commit()

    def record_packet(
        self,
        packet: AdvertisementPacket,
        filtered_rssi: float,
        distance: float,
        variance: float,
        is_motion: bool,
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO packets (
                    timestamp, address, name, rssi, filtered_rssi,
                    tx_power, distance, variance, is_motion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    packet.timestamp,
                    packet.address,
                    packet.name,
                    packet.rssi,
                    filtered_rssi,
                    packet.tx_power,
                    distance,
                    variance,
                    1 if is_motion else 0,
                ),
            )
            conn.commit()

    def fetch_recent(self, address: str, limit: int = 50) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM packets
                WHERE address = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (address, limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    def export_csv(self, output_path: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM packets ORDER BY timestamp ASC")
            rows = cursor.fetchall()

            if not rows:
                return 0

            fieldnames = rows[0].keys()
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for r in rows:
                    writer.writerow(dict(r))
            return len(rows)
