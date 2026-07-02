from typing import Tuple


def _digits_only(value: str) -> str:
    """
    Remove everything except 0-9 digits.
    Handles things like: '+971-55-9186483', " '918947463244", spaces, etc.
    """
    value = value or ""
    # Remove leading apostrophe from Excel/POS exports
    value = value.strip().lstrip("'")
    return "".join(ch for ch in value if ch.isdigit())


def _detect_country_code(digits: str) -> str:
    """
    Detect country code based on prefix and/or length.
    Currently supports: +971 (UAE), +91 (India), +86 (China).
    Fallback default: +971.
    """
    if not digits:
        return "+971"

    # Prefix-based detection first
    if digits.startswith("971"):
        return "+971"
    if digits.startswith("91") and not digits.startswith("971"):
        return "+91"
    if digits.startswith("86"):
        return "+86"

    # Length-based fallback (when prefix isn't clear)
    length = len(digits)
    if length == 10:
        # Typical Indian mobile without country code
        return "+91"
    if length == 9:
        # Typical UAE mobile without country code
        return "+971"
    if length == 11:
        # China pattern (can adjust as needed)
        return "+86"

    # Safe default
    return "+971"


def _normalize_country_code(raw_code: str | None, digits: str) -> str:
    """
    If sheet has a separate country_code column, normalize that.
    Example inputs: '+971', '971', '91 ', ' +86', etc.
    If empty/invalid, detect from digits.
    """
    raw_code = (raw_code or "").strip()
    if not raw_code:
        return _detect_country_code(digits)

    # Take only digits from the country_code cell
    cc_digits = _digits_only(raw_code)
    if cc_digits == "971":
        return "+971"
    if cc_digits == "91":
        return "+91"
    if cc_digits == "86":
        return "+86"

    # If something else, fall back to auto-detect from digits
    return _detect_country_code(digits)


def _strip_country_code(digits: str, country_code: str) -> str:
    """
    Remove country code from full digits to get local number.
    If prefix detection fails, use length-based fallback.
    """
    cc_digits = country_code.lstrip("+")
    if digits.startswith(cc_digits):
        local = digits[len(cc_digits):]
    else:
        # Fallbacks based on typical lengths
        if country_code == "+91" and len(digits) >= 10:
            local = digits[-10:]
        elif country_code == "+971" and len(digits) >= 9:
            local = digits[-9:]
        elif country_code == "+86" and len(digits) >= 11:
            local = digits[-11:]
        else:
            # If completely unknown, keep digits as-is
            local = digits
    return local


def normalize_phone(raw_phone: str, raw_country_code: str | None = None) -> Tuple[str, str]:
    """
    Main helper to normalize phone.
    Returns: (country_code, local_number)

    - Cleans characters: '+', '-', ' ', '(', ')', leading "'".
    - Auto-detects country code if not given.
    - Returns local_number without country code (for session keys).
    """
    digits = _digits_only(raw_phone)
    if not digits:
        return "", ""

    country_code = _normalize_country_code(raw_country_code, digits)
    local_number = _strip_country_code(digits, country_code)
    return country_code, local_number