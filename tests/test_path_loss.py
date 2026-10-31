import pytest
from prober.dsp.path_loss import LogDistancePathLoss


def test_distance_at_one_meter():
    pl = LogDistancePathLoss(reference_tx_power=-59.0, path_loss_exponent=2.0)
    # When RSSI == TxPower, distance should be exactly 1.0 m
    dist = pl.estimate_distance(-59.0)
    assert pytest.approx(dist, rel=1e-3) == 1.0


def test_distance_scaling():
    pl = LogDistancePathLoss(reference_tx_power=-60.0, path_loss_exponent=2.0)
    # At -80 dBm with n=2.0: exponent = ( -60 - (-80) ) / 20 = 20 / 20 = 1.0 -> 10^1 = 10m
    dist = pl.estimate_distance(-80.0)
    assert pytest.approx(dist, rel=1e-3) == 10.0

    # Stronger signal -> smaller distance
    dist_close = pl.estimate_distance(-50.0)
    assert dist_close < 1.0


def test_distance_clamping():
    pl = LogDistancePathLoss(min_distance=0.1, max_distance=30.0)
    assert pl.estimate_distance(-130.0) == 30.0
    assert pl.estimate_distance(5.0) == 0.1


def test_calibration_reference_power():
    pl = LogDistancePathLoss()
    samples = [-58.0, -60.0, -59.0]
    calibrated = pl.calibrate_reference_power(samples)
    assert calibrated == -59.0
    assert pl.reference_tx_power == -59.0


def test_calibration_exponent():
    pl = LogDistancePathLoss(reference_tx_power=-60.0)
    # Measured -80 dBm at 10 meters -> n should be 1.0
    n = pl.calibrate_exponent(measured_rssi=-80.0, known_distance=10.0, reference_power=-60.0)
    assert pytest.approx(n, rel=1e-2) == 2.0
