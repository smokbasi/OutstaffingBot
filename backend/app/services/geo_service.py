import math
from decimal import Decimal


def haversine_km(lat1: Decimal | float, lon1: Decimal | float, lat2: Decimal | float, lon2: Decimal | float) -> float:
    """Great-circle distance in km (no PostGIS — lat/lon on metro stations)."""
    r = 6371.0
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    d_phi = math.radians(float(lat2) - float(lat1))
    d_lambda = math.radians(float(lon2) - float(lon1))
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def haversine_sql_expr(
    worker_lat_col,
    worker_lon_col,
    job_lat_col,
    job_lon_col,
):
    """SQLAlchemy expression approximating haversine distance in km."""
    from sqlalchemy import cast, func
    from sqlalchemy.types import Float

    lat1 = cast(worker_lat_col, Float)
    lon1 = cast(worker_lon_col, Float)
    lat2 = cast(job_lat_col, Float)
    lon2 = cast(job_lon_col, Float)
    d_lat = func.radians(lat2 - lat1)
    d_lon = func.radians(lon2 - lon1)
    a = (
        func.power(func.sin(d_lat / 2), 2)
        + func.cos(func.radians(lat1)) * func.cos(func.radians(lat2)) * func.power(func.sin(d_lon / 2), 2)
    )
    return 6371.0 * 2 * func.asin(func.sqrt(func.least(a, 1.0)))
