BLOCKED_NUMBERS = [
    "5491171950001",
]


def is_number_blocked(phone_number: str) -> bool:
    """
    Check if a given phone number is blocked.

    Args:
    phone_number (str): The phone number to check.

    Returns:
    bool: True if the number is blocked, False otherwise.
    """
    return phone_number in BLOCKED_NUMBERS
