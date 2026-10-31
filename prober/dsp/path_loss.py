import math
from typing import Optional, Sequence


class LogDistancePathLoss:
    """
    Log-Distance Path Loss Model for radio distance estimation.
    Formula: RSSI = TxPower - 10 * n * log10(d)
    Solving for distance: d = 10 ** ((TxPower - RSSI) / (10 * n))
    """

    def __init__(
        self,
        reference_tx_power: float = -59.0,
        path_loss_exponent: float = 2.4,
        min_distance: float = 0.05,
        max_distance: float = 50.0,
    ):
        self.reference_tx_power = reference_tx_power
        self.n = path_loss_exponent
        self.min_distance = min_distance
        self.max_distance = max_distance

    def estimate_distance(
        self,
        rssi: float,
        tx_power: Optional[float] = None,
    ) -> float:
        """
        Estimate distance in meters from RSSI and optional calibrated TxPower.
        """
        p_ref = tx_power if tx_power is not None else self.reference_tx_power

        # Safeguard against positive or non-physical RSSI values
        if rssi >= 0.0:
            return self.min_distance

        exponent = (p_ref - rssi) / (10.0 * self.n)
        try:
            distance = math.pow(10.0, exponent)
        except OverflowError:
            distance = self.max_distance

        return max(self.min_distance, min(self.max_distance, distance))

    def calibrate_reference_power(self, measured_rssi_1m: Sequence[float]) -> float:
        """
        Calibrate reference TxPower (RSSI at 1 meter) using measured RSSI values.
        """
        if not measured_rssi_1m:
            return self.reference_tx_power
        self.reference_tx_power = float(sum(measured_rssi_1m) / len(measured_rssi_1m))
        return self.reference_tx_power

    def calibrate_exponent(
        self,
        measured_rssi: float,
        known_distance: float,
        reference_power: Optional[float] = None,
    ) -> float:
        """
        Compute path loss exponent n from a measured RSSI at a known distance (> 0.1m).
        """
        p_ref = reference_power if reference_power is not None else self.reference_tx_power
        if known_distance <= 0.1:
            return self.n

        # n = (P_ref - RSSI) / (10 * log10(d))
        denom = 10.0 * math.log10(known_distance)
        if abs(denom) < 1e-6:
            return self.n

        calc_n = (p_ref - measured_rssi) / denom
        if 1.2 <= calc_n <= 5.0:
            self.n = calc_n
        return self.n
