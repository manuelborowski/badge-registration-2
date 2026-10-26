"""Per-user client IP policy using nginx's X-Real-IP header."""
from ipaddress import ip_address


def user_ip_allowed(user, environ):
    if user is None:
        return False
    # nginx must overwrite this header; only nginx should reach the backend.
    address = environ.get('HTTP_X_REAL_IP', environ.get('REMOTE_ADDR'))
    try:
        address = ip_address(address)
    except (ValueError, TypeError):
        return False
    return address.is_private or bool(user.remote)
