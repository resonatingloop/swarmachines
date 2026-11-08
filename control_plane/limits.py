"""Small local reservation policies; not account quotas or spending authority."""

DEFAULT = {
    "request_limit": 4,
    "credit_limit_micro": 1_000_000,
    "reservation_micro": 100_000,
}
SESSION = {
    "request_limit": 20,
    "credit_limit_micro": 2_000_000,
    "reservation_micro": 100_000,
}


def validate_limits(value):
    """Return an owned bounded policy; refuse unknown fields and booleans."""
    if not isinstance(value, dict) or set(value) != set(DEFAULT):
        raise ValueError("invalid reservation policy")
    if any(type(v) is not int for v in value.values()):
        raise ValueError("noninteger reservation policy")
    if (
        not 1 <= value["request_limit"] <= 20
        or not 100_000 <= value["credit_limit_micro"] <= 2_000_000
        or value["reservation_micro"] != 100_000
    ):
        raise ValueError("reservation policy exceeds supported bounds")
    return dict(value)
