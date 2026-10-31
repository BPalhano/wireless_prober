from typing import Optional


class RSSIStateFilter:
    """
    1D Kalman Filter for BLE RSSI signals.
    Reduces Gaussian multipath noise and sudden shadowing fluctuations.
    """

    def __init__(
        self,
        process_noise_q: float = 0.12,
        measurement_noise_r: float = 3.50,
        initial_rssi: Optional[float] = None,
        outlier_threshold_db: float = 25.0,
    ):
        self.q = process_noise_q
        self.r = measurement_noise_r
        self.outlier_threshold_db = outlier_threshold_db

        self.x = initial_rssi if initial_rssi is not None else -65.0
        self.p = 1.0
        self.initialized = initial_rssi is not None

    def update(self, measurement: float) -> float:
        if not self.initialized:
            self.x = measurement
            self.p = self.r
            self.initialized = True
            return self.x

        # Soft outlier damping: limit extreme jumps
        delta = abs(measurement - self.x)
        if delta > self.outlier_threshold_db:
            if measurement > self.x:
                measurement = self.x + self.outlier_threshold_db
            else:
                measurement = self.x - self.outlier_threshold_db

        # 1. Predict
        x_pred = self.x
        p_pred = self.p + self.q

        # 2. Kalman Gain
        k_gain = p_pred / (p_pred + self.r)

        # 3. Update
        self.x = x_pred + k_gain * (measurement - x_pred)
        self.p = (1.0 - k_gain) * p_pred

        return self.x

    def reset(self, initial_rssi: Optional[float] = None) -> None:
        self.x = initial_rssi if initial_rssi is not None else -65.0
        self.p = 1.0
        self.initialized = initial_rssi is not None
