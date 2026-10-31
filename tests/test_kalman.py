import pytest
import numpy as np
from prober.dsp.kalman import RSSIStateFilter


def test_kalman_initialization():
    f = RSSIStateFilter(initial_rssi=-70.0)
    assert f.x == -70.0
    assert f.initialized is True


def test_kalman_noise_reduction():
    np.random.seed(42)
    true_rssi = -60.0
    noise = np.random.normal(0, 4.0, 50)
    measurements = true_rssi + noise

    kf = RSSIStateFilter(initial_rssi=measurements[0], process_noise_q=0.08, measurement_noise_r=4.0)
    filtered = [kf.update(m) for m in measurements]

    # Filtered variance should be significantly lower than raw measurement variance
    assert np.var(filtered[10:]) < np.var(measurements[10:])
    # Final estimate should be close to true value
    assert abs(filtered[-1] - true_rssi) < 2.5


def test_kalman_outlier_rejection():
    kf = RSSIStateFilter(initial_rssi=-65.0, outlier_threshold_db=20.0)
    # Feed an impossible outlier (+10 dBm)
    filtered = kf.update(10.0)
    # Outlier should be clamped and not immediately pull the filter
    assert filtered < -40.0
