"""Order checkout.

The rules live in `src/shop/specs/checkout.md` - read it first.
The signatures and the constants below are final: the tests rely on them.
"""

from shop.money import percent_of

PROMO_CODES = {"WELCOME10": 10, "SUMMER15": 15, "VIP35": 35}
SUPPORTED_CITIES = ("msk", "spb")
MAX_DISCOUNT_PERCENT = 30
VAT_PERCENT = 20
SHIPPING_KOPEKS = 49_000
FREE_DELIVERY_FROM_KOPEKS = 500_000
TIER_DISCOUNTS = ((10, 5), (25, 10), (50, 15))
REQUIRED_LINE_KEYS = ("sku", "qty", "unit_price_kopecks")


def _parse_int(value: object) -> int | None:
    """Return `value` as an integer, or None when it is not a whole number.

    The grammar mirrors `int()` on a decimal string: optional sign, decimal
    digits, single underscores between digits. The grammar is checked before
    the conversion because exceptions are forbidden in this project.
    """
    if not isinstance(value, str):
        return None
    body = value.strip()
    sign = -1 if body[:1] == "-" else 1
    if body[:1] in ("+", "-"):
        body = body[1:]
    digits = body.split("_")
    if any(not part.isdecimal() for part in digits):
        return None
    return sign * int("".join(digits))


def _validate_numbers(index: int, line: dict[str, str]) -> str | None:
    """Return an error for the numbers of a single line, or None (spec rules 4-7)."""
    qty = _parse_int(line["qty"])
    if qty is None:
        return f"line {index} qty must be a whole number"
    if qty <= 0:
        return f"line {index} qty must be greater than zero"

    price = _parse_int(line["unit_price_kopecks"])
    if price is None:
        return f"line {index} unit_price_kopecks must be a whole number"
    if price < 0:
        return f"line {index} unit_price_kopecks must not be negative"

    return None


def _validate_line(index: int, line: object) -> str | None:
    """Return an error for a single line, or None if the line is valid."""
    if not isinstance(line, dict):
        return f"line {index} must be an object"

    if "sku" in line and not line["sku"]:
        return f"line {index} sku must not be empty"

    for key in REQUIRED_LINE_KEYS:
        if key not in line:
            return f"line {index} is missing required key: {key}"

    return _validate_numbers(index, line)


def _find_duplicate_sku(lines: list[dict[str, str]]) -> str | None:
    """Return the sku that appears twice, or None when every sku is unique."""
    seen: set[str] = set()
    for line in lines:
        sku = line["sku"]
        if sku in seen:
            return sku
        seen.add(sku)
    return None


def validate_order(
    lines: list[dict[str, str]],
    promo_code: str = "",
    shipping_city: str = "",
) -> str | None:
    """Return a human readable reason why the order is invalid, or None if it is fine."""
    if not lines:
        return "order must contain at least one line"

    for index, line in enumerate(lines, start=1):
        error = _validate_line(index, line)
        if error is not None:
            return error

    duplicate = _find_duplicate_sku(lines)
    if duplicate is not None:
        return f"sku must not repeat: {duplicate}"

    if promo_code and promo_code not in PROMO_CODES:
        return f"unknown promo code: {promo_code}"

    if shipping_city and shipping_city not in SUPPORTED_CITIES:
        return f"unsupported shipping city: {shipping_city}"

    return None


def _discount_percent(total_qty: int, promo_code: str) -> int:
    """Pick the bigger of the tier and promo percentages, capped at the maximum."""
    tier = 0
    for threshold, percent in TIER_DISCOUNTS:
        if total_qty >= threshold:
            tier = percent

    promo = PROMO_CODES.get(promo_code, 0)

    return min(max(tier, promo), MAX_DISCOUNT_PERCENT)


def calculate_order_total(
    lines: list[dict[str, str]],
    promo_code: str = "",
    shipping_city: str = "",
) -> int | None:
    """Return the order total in kopecks, or None if the order is invalid."""
    if validate_order(lines, promo_code, shipping_city) is not None:
        return None

    subtotal = 0
    total_qty = 0
    for line in lines:
        # Validation already rejected unparsable values, so only the type needs fixing.
        qty = _parse_int(line["qty"]) or 0
        price = _parse_int(line["unit_price_kopecks"]) or 0
        subtotal += qty * price
        total_qty += qty

    discount = percent_of(subtotal, _discount_percent(total_qty, promo_code))
    discounted_subtotal = subtotal - discount

    delivery = 0
    if shipping_city and discounted_subtotal < FREE_DELIVERY_FROM_KOPEKS:
        delivery = SHIPPING_KOPEKS

    base = discounted_subtotal + delivery
    vat = percent_of(base, VAT_PERCENT)
    return base + vat
