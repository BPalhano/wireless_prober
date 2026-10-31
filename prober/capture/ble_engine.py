import asyncio
import time
from typing import Callable, Optional, Set
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from ..core.models import AdvertisementPacket


class BLECaptureEngine:
    """
    Asynchronous continuous BLE advertising packet stream.
    Receives live advertising packets via Bleak and dispatches structured AdvertisementPacket instances.
    """

    def __init__(
        self,
        packet_callback: Optional[Callable[[AdvertisementPacket], None]] = None,
        target_macs: Optional[Set[str]] = None,
        min_rssi: float = -100.0,
    ):
        self.packet_callback = packet_callback
        self.target_macs = {m.upper() for m in target_macs} if target_macs else None
        self.min_rssi = min_rssi
        self.scanner: Optional[BleakScanner] = None
        self._is_running = False

    def _on_detection(self, device: BLEDevice, adv_data: AdvertisementData) -> None:
        addr = device.address.upper()
        if self.target_macs and addr not in self.target_macs:
            return

        rssi = adv_data.rssi if adv_data.rssi is not None else -100.0
        if rssi < self.min_rssi:
            return

        # Format manufacturer data as hex
        mfg_dict = {}
        if adv_data.manufacturer_data:
            for company_id, data_bytes in adv_data.manufacturer_data.items():
                mfg_dict[company_id] = data_bytes.hex()

        # Format service data as hex
        svc_dict = {}
        if adv_data.service_data:
            for uuid_str, data_bytes in adv_data.service_data.items():
                svc_dict[uuid_str] = data_bytes.hex()

        packet = AdvertisementPacket(
            timestamp=time.time(),
            address=addr,
            name=device.name or adv_data.local_name,
            rssi=float(rssi),
            tx_power=adv_data.tx_power,
            manufacturer_data=mfg_dict,
            service_uuids=list(adv_data.service_uuids or []),
            service_data=svc_dict,
        )

        if self.packet_callback:
            self.packet_callback(packet)

    async def start(self) -> None:
        if self._is_running:
            return
        self.scanner = BleakScanner(detection_callback=self._on_detection)
        await self.scanner.start()
        self._is_running = True

    async def stop(self) -> None:
        if not self._is_running or not self.scanner:
            return
        try:
            await self.scanner.stop()
        except Exception:
            pass
        finally:
            self._is_running = False

    async def capture_stream(self, duration: Optional[float] = None) -> None:
        """
        Runs capture loop for a set duration or indefinitely until interrupted.
        """
        await self.start()
        try:
            if duration is not None:
                await asyncio.sleep(duration)
            else:
                while self._is_running:
                    await asyncio.sleep(0.5)
        finally:
            await self.stop()
