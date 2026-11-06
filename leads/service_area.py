"""Basic service-area sanity check for inbound leads (not geo/routing)."""

from marketing.demo import SERVICE_AREA_ZIPS


def normalize_zip(value: str) -> str:
    digits = "".join(ch for ch in (value or "") if ch.isdigit())
    return digits[:5]


def zip_in_service_area(value: str) -> bool:
    z = normalize_zip(value)
    if not z:
        return False
    return z in SERVICE_AREA_ZIPS
