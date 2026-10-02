"""Order checkout.

The rules live in `src/shop/specs/checkout.md` - read it first.
Both functions below are stubs: their signature is final, the bodies are yours.
Do not change the constants: the tests rely on them.
"""

PROMO_CODES = {"WELCOME10": 10, "SUMMER15": 15, "VIP35": 35}
SUPPORTED_CITIES = ("msk", "spb")
MAX_DISCOUNT_PERCENT = 30
VAT_PERCENT = 20
SHIPPING_KOPEKS = 49_000
FREE_DELIVERY_FROM_KOPEKS = 500_000
TIER_DISCOUNTS = ((10, 5), (25, 10), (50, 15))
REQUIRED_LINE_KEYS = ("sku", "qty", "unit_price_kopecks")


def _validate_line(index: int, line: object) -> str | None:
    """Return an error for a single line, or None if the line is valid."""
    if not isinstance(line, dict):
        return f"line {index} must be an object"

    for key in REQUIRED_LINE_KEYS:
        if key not in line:
            return f"line {index} is missing required key: {key}"

    try:
        qty = int(line["qty"])
        unit_price = int(line["unit_price_kopecks"])
    except (TypeError, ValueError):
        return f"line {index} has non-numeric qty or unit_price_kopecks"

    if qty <= 0:
        return f"line {index} qty must be positive"

    if unit_price < 0:
        return f"line {index} unit_price_kopecks must not be negative"

    return None


def validate_order(
    lines: list[dict[str, str]],
    promo_code: str = "",
    shipping_city: str = "",
) -> str | None:
    """Return a human readable reason why the order is invalid, or None if it is fine."""
    if not lines:
        return "order must contain at least one line"

    for index, line in enumerate(lines):
        error = _validate_line(index, line)
        if error is not None:
            return error

    if promo_code and promo_code not in PROMO_CODES:
        return f"unknown promo code: {promo_code}"

    if shipping_city and shipping_city not in SUPPORTED_CITIES:
        return f"unsupported shipping city: {shipping_city}"

    return None


def _max_discount_percent(lines: list[dict[str, str]], promo_code: str) -> int:
    total_qty = sum(int(line["qty"]) for line in lines)

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

    subtotal = sum(int(line["qty"]) * int(line["unit_price_kopecks"]) for line in lines)

    discount_percent = _max_discount_percent(lines, promo_code)
    discount = subtotal * discount_percent // 100
    net = subtotal - discount

    vat = net * VAT_PERCENT // 100
    total = net + vat

    if shipping_city:
        shipping = 0 if subtotal >= FREE_DELIVERY_FROM_KOPEKS else SHIPPING_KOPEKS
        total += shipping

    return total
