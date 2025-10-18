from datetime import datetime


def format_datetime_utc(dt: datetime) -> str:
    """
    datetime 객체를 UTC ISO 형식 문자열로 변환
    SQLite는 timezone 정보를 저장하지 않으므로 +00:00을 명시적으로 추가

    Args:
        dt: datetime 객체

    Returns:
        ISO 형식 문자열 (예: 2025-10-05T12:34:56+00:00)
        dt가 None이면 빈 문자열 반환
    """
    if not dt:
        return ''

    iso_str = dt.isoformat()

    # timezone 정보가 없으면 UTC로 명시
    if '+' not in iso_str and not iso_str.endswith('Z'):
        iso_str += '+00:00'

    return iso_str
