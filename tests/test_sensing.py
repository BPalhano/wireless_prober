from prober.dsp.sensing import RadioSensingDetector


def test_sensing_stable_channel():
    detector = RadioSensingDetector(window_size=10, variance_threshold_db2=3.0)
    stable_samples = [-65.0, -65.2, -64.9, -65.1, -65.0, -65.1, -64.8, -65.0]

    for s in stable_samples:
        var, motion = detector.update(s)

    assert motion is False
    assert var < 1.0


def test_sensing_motion_perturbation():
    detector = RadioSensingDetector(window_size=10, variance_threshold_db2=3.0)
    # High fluctuation mimicking multipath scattering from moving person
    fluctuating_samples = [-65.0, -74.0, -58.0, -72.0, -60.0, -78.0, -55.0]

    motion_detected = False
    for s in fluctuating_samples:
        var, motion = detector.update(s)
        if motion:
            motion_detected = True

    assert motion_detected is True
    assert var >= 3.0
