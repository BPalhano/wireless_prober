from dataclasses import dataclass
from typing import List, Tuple, Optional
import math
import numpy as np
from scipy.optimize import least_squares


@dataclass
class AnchorNode:
    name: str
    x: float
    y: float


def trilaterate_2d(
    anchors: List[Tuple[float, float]],
    distances: List[float],
) -> Tuple[float, float, float]:
    """
    Compute 2D estimated position (x, y) using Non-Linear Least Squares (NLS).
    Residual: f_i(x, y) = sqrt((x - x_i)^2 + (y - y_i)^2) - d_i

    Returns:
        (est_x, est_y, residual_rmse)
    """
    if len(anchors) < 3 or len(distances) < 3:
        raise ValueError("At least 3 anchors and distances are required for 2D trilateration.")

    anchors_arr = np.array(anchors, dtype=np.float64)
    dists_arr = np.array(distances, dtype=np.float64)

    # Initial guess: weighted centroid by inverse distance
    weights = 1.0 / np.maximum(dists_arr, 0.05)
    init_x = float(np.sum(anchors_arr[:, 0] * weights) / np.sum(weights))
    init_y = float(np.sum(anchors_arr[:, 1] * weights) / np.sum(weights))
    x0 = np.array([init_x, init_y], dtype=np.float64)

    def residuals(point: np.ndarray) -> np.ndarray:
        dx = anchors_arr[:, 0] - point[0]
        dy = anchors_arr[:, 1] - point[1]
        calc_dist = np.sqrt(dx ** 2 + dy ** 2)
        return calc_dist - dists_arr

    # Robust least squares with soft_l1 loss to attenuate multipath outliers
    result = least_squares(residuals, x0, loss="soft_l1", f_scale=1.0)

    est_x, est_y = float(result.x[0]), float(result.x[1])
    rmse = float(np.sqrt(np.mean(residuals(result.x) ** 2)))

    return est_x, est_y, rmse
