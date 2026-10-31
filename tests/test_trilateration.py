import pytest
from prober.localization.trilateration import trilaterate_2d


def test_trilateration_ideal():
    # 3 anchors at known positions
    anchors = [(0.0, 0.0), (10.0, 0.0), (0.0, 10.0)]
    # Target at (3.0, 4.0)
    # dist to (0,0) = 5.0
    # dist to (10,0) = sqrt(7^2 + 4^2) = sqrt(65) ~= 8.062
    # dist to (0,10) = sqrt(3^2 + 6^2) = sqrt(45) ~= 6.708
    distances = [5.0, 8.0622577, 6.7082039]

    est_x, est_y, rmse = trilaterate_2d(anchors, distances)

    assert pytest.approx(est_x, abs=0.1) == 3.0
    assert pytest.approx(est_y, abs=0.1) == 4.0
    assert rmse < 0.05


def test_trilateration_insufficient_anchors():
    with pytest.raises(ValueError):
        trilaterate_2d([(0.0, 0.0), (1.0, 1.0)], [2.0, 3.0])
