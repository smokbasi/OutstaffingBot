import math
from decimal import Decimal

import pytest

from app.services.geo_service import haversine_km


def test_haversine_same_point_is_zero():
    assert haversine_km(Decimal("59.93"), Decimal("30.31"), Decimal("59.93"), Decimal("30.31")) == 0.0


def test_haversine_spb_metro_distance_reasonable():
    # Автово — Невский проспект ~ 8 km
    distance = haversine_km(
        Decimal("59.8673"),
        Decimal("30.2614"),
        Decimal("59.9356"),
        Decimal("30.3275"),
    )
    assert 5 < distance < 12


def test_haversine_symmetry():
    a = haversine_km(59.9, 30.3, 60.0, 30.4)
    b = haversine_km(60.0, 30.4, 59.9, 30.3)
    assert math.isclose(a, b, rel_tol=1e-6)
