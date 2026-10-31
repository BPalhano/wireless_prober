from collections import deque
from typing import Tuple
import math


class RadioSensingDetector:
    """
    Device-Free / Line-of-Sight RF Sensing Detector.
    Tracks RSSI temporal variance over a sliding window.
    Perturbations indicate human motion or moving obstacles across RF propagation paths.
    """

    def __init__(
        self,
        window_size: int = 15,
        variance_threshold_db2: float = 3.5,
        min_samples: int = 5,
    ):
        self.window_size = window_size
        self.threshold = variance_threshold_db2
        self.min_samples = min_samples
        self.window: deque = deque(maxlen=window_size)

    def update(self, rssi: float) -> Tuple[float, bool]:
        """
        Add a new RSSI sample, calculate current variance, and detect perturbation.
        Returns: (current_variance, is_motion_detected)
        """
        self.window.append(rssi)

        if len(self.window) < self.min_samples:
            return 0.0, False

        mean = sum(self.window) / len(self.window)
        variance = sum((x - mean) ** 2 for x in self.window) / len(self.window)
        is_motion = variance >= self.threshold

        return variance, is_motion

    def reset(self) -> None:
        self.window.clear()
