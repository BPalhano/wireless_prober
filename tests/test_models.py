import pytest
import time
import os
from prober.core.models import AdvertisementPacket, DeviceTelemetry
from prober.storage.timeseries import TelemetryDatabase


def test_telemetry_rate():
    dev = DeviceTelemetry(address="AA:BB:CC:DD:EE:FF")
    t0 = time.time()
    pkt1 = AdvertisementPacket(timestamp=t0, address="AA:BB:CC:DD:EE:FF", rssi=-60.0)
    pkt2 = AdvertisementPacket(timestamp=t0 + 0.5, address="AA:BB:CC:DD:EE:FF", rssi=-62.0)
    pkt3 = AdvertisementPacket(timestamp=t0 + 1.0, address="AA:BB:CC:DD:EE:FF", rssi=-61.0)

    dev.update(pkt1, -60.0, 1.0, 0.1, False)
    dev.update(pkt2, -61.0, 1.1, 0.2, False)
    dev.update(pkt3, -61.0, 1.1, 0.2, False)

    assert dev.packet_count == 3
    assert pytest.approx(dev.packet_rate, rel=0.1) == 2.0


def test_sqlite_storage(tmp_path):
    db_file = tmp_path / "test.db"
    db = TelemetryDatabase(str(db_file))

    pkt = AdvertisementPacket(
        timestamp=time.time(),
        address="11:22:33:44:55:66",
        name="BeaconTag",
        rssi=-75.0,
        tx_power=-59,
    )
    db.record_packet(pkt, filtered_rssi=-74.5, distance=3.2, variance=1.1, is_motion=False)

    recent = db.fetch_recent("11:22:33:44:55:66")
    assert len(recent) == 1
    assert recent[0]["name"] == "BeaconTag"
    assert recent[0]["rssi"] == -75.0
    assert recent[0]["distance"] == 3.2

    csv_file = tmp_path / "export.csv"
    count = db.export_csv(str(csv_file))
    assert count == 1
    assert os.path.exists(csv_file)
