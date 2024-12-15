from typing import Dict, List

# Default admin password: "admin"
# Default user password: "user"
DEFAULT_USERS: Dict[str, List] = {
    "admin": {
        "password_hash": "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918",
        "run_behaviors": True,
        "edit_behavior": True,
        "edit_tool": True,
        "clear_alerts": True,
        "edit_users": True,
        "timeout_minutes": 10},
    "user": {
        "password_hash": "04f8996da763b7a969b1028ee3007569eaf3a635486ddab211d512c85b9df8fb",
        "run_behaviors": True,
        "edit_behavior": False,
        "edit_tool": False,
        "clear_alerts": True,
        "edit_users": False,
        "timeout_minutes": 111}
}

# Password policy
MIN_PASSWORD_LENGTH = 8
REQUIRE_SPECIAL_CHARS = True
REQUIRE_NUMBERS = True
SESSION_TIMEOUT_MINUTES = 30
