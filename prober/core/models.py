from dataclasses import dataclass, field
from typing import Optional, Dict, List
from collections import deque
import time


@dataclass
class AdvertisementPacket:
    timestamp: float
    address: str
    name: Optional[str] = None
    rssi: float = 0.0
    tx_power: Optional[int] = None
    manufacturer_data: Dict[int, str] = field(default_factory=dict)
    service_uuids: List[str] = field(default_factory=list)
    service_data: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "address": self.address,
            "name": self.name,
            "rssi": self.rssi,
            "tx_power": self.tx_power,
            "manufacturer_data": self.manufacturer_data,
            "service_uuids": self.service_uuids,
            "service_data": self.service_data,
        }


@dataclass
class DeviceTelemetry:
    address: str
    name: Optional[str] = None
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    packet_count: int = 0
    raw_rssi: float = 0.0
    filtered_rssi: float = 0.0
    estimated_distance: float = 0.0
    rssi_variance: float = 0.0
    is_motion_detected: bool = False
    rssi_history: deque = field(default_factory=lambda: deque(maxlen=60))
    timestamps: deque = field(default_factory=lambda: deque(maxlen=60))

    def update(
        self,
        packet: AdvertisementPacket,
        filtered_rssi: float,
        distance: float,
        variance: float,
        is_motion: bool,
    ) -> None:
        self.last_seen = packet.timestamp
        self.packet_count += 1
        if packet.name:
            self.name = packet.name
        self.raw_rssi = packet.rssi
        self.filtered_rssi = filtered_rssi
        self.estimated_distance = distance
        self.rssi_variance = variance
        self.is_motion_detected = is_motion
        self.rssi_history.append(packet.rssi)
        self.timestamps.append(packet.timestamp)

    @property
    def packet_rate(self) -> float:
        """Packet rate in packets per second (Hz) calculated over recent history."""
        if len(self.timestamps) < 2:
            return 0.0
        elapsed = self.timestamps[-1] - self.timestamps[0]
        if elapsed <= 0.0:
            return 0.0
        return (len(self.timestamps) - 1) / elapsed
