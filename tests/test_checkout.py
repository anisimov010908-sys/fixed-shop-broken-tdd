"""Order checkout, part 2.

How to work through this file:

1. The single red test below is done for you - it shows what RED looks like.
2. Run `./scripts/check-part2.sh` and read the failure.
3. Write one assertion per rule from `src/shop/specs/checkout.md` into the empty
   tests: a failing test first, then the code that makes it pass.
4. Never edit a finished assertion, never `skip`, never weaken a test.

Run one test at a time while you work:

    uv run pytest tests/test_checkout.py -k tier -x
"""

from shop.checkout import calculate_order_total, validate_order


def line(sku: str = "SKU-1", qty: str = "1", unit_price_kopecks: str = "10000") -> dict[str, str]:
    """Build one order line the way the warehouse export delivers it."""
    return {"sku": sku, "qty": qty, "unit_price_kopecks": unit_price_kopecks}


def test_smoke_single_line_without_delivery() -> None:
    """One line, no promo code, no delivery. Works out to 100.00 rub + 20% VAT."""
    assert validate_order([line()]) is None
    assert calculate_order_total([line()]) == 12_000


def test_empty_order_is_rejected() -> None:
    """Spec 3, rule 1: an order without lines cannot be processed."""
    reason = validate_order([])
    assert reason is not None
    assert reason.strip()
    assert calculate_order_total([]) is None


def test_empty_sku_is_rejected() -> None:
    """Spec 3, rule 2: a blank article code is not allowed."""
    blank = line(sku="")
    reason = validate_order([blank])
    assert reason is not None
    assert reason.strip()
    assert calculate_order_total([blank]) is None


def test_missing_line_key_is_rejected() -> None:
    """Spec 3, rule 3: every required key must be present."""
    incomplete = {"sku": "SKU-1", "qty": "1"}
    reason = validate_order([incomplete])
    assert reason is not None
    assert reason.strip()
    assert calculate_order_total([incomplete]) is None


def test_non_numeric_quantity_is_rejected() -> None:
    """Spec 3, rule 4: `qty` must be a whole number."""
    words = line(qty="two")
    reason = validate_order([words])
    assert reason is not None
    assert reason.strip()
    assert calculate_order_total([words]) is None


def test_zero_quantity_is_rejected() -> None:
    """Spec 3, rule 5: `qty` must be greater than zero."""
    zero = line(qty="0")
    negative = line(sku="SKU-2", qty="-3")
    reason = validate_order([zero])
    assert reason is not None
    assert reason.strip()
    assert validate_order([negative]) is not None
    assert calculate_order_total([zero]) is None
    assert calculate_order_total([negative]) is None


def test_non_numeric_price_is_rejected() -> None:
    """Spec 3, rule 6: `unit_price_kopecks` must be a whole number."""
    fractional = line(unit_price_kopecks="10.5")
    reason = validate_order([fractional])
    assert reason is not None
    assert reason.strip()
    assert calculate_order_total([fractional]) is None


def test_negative_price_is_rejected() -> None:
    """Spec 3, rule 7: a price may not be negative."""
    underpriced = line(unit_price_kopecks="-100")
    reason = validate_order([underpriced])
    assert reason is not None
    assert reason.strip()
    assert calculate_order_total([underpriced]) is None


def test_duplicate_sku_is_rejected() -> None:
    """Spec 3, rule 8: the same article may appear only once."""
    twice = [line(), line(sku="SKU-1", qty="2")]
    reason = validate_order(twice)
    assert reason is not None
    assert reason.strip()
    assert calculate_order_total(twice) is None


def test_unknown_promo_code_is_rejected() -> None:
    """Spec 3, rule 9: only codes from PROMO_CODES exist."""
    reason = validate_order([line()], promo_code="NOPE")
    assert reason is not None
    assert reason.strip()
    assert calculate_order_total([line()], promo_code="NOPE") is None


def test_unsupported_city_is_rejected() -> None:
    """Spec 3, rule 10: only cities from SUPPORTED_CITIES are served."""
    reason = validate_order([line()], shipping_city="kzn")
    assert reason is not None
    assert reason.strip()
    assert calculate_order_total([line()], shipping_city="kzn") is None


def test_valid_order_passes_validation() -> None:
    """Spec 3: a good order gets None back instead of a reason."""
    assert validate_order([line()], promo_code="WELCOME10", shipping_city="msk") is None
    assert calculate_order_total([line()], promo_code="WELCOME10") == 10_800


def test_no_discount_below_first_tier() -> None:
    """Spec 4, steps 1-2: 9 units are below every threshold."""
    nine = [line(qty="9", unit_price_kopecks="1000")]
    assert calculate_order_total(nine) == 10_800


def test_tier_discount_at_first_threshold() -> None:
    """Spec 4, steps 2-5: 10 units give 5%. Compare with example 2."""
    ten = [line(qty="10", unit_price_kopecks="1990")]
    assert calculate_order_total(ten) == 22_686


def test_tier_discount_at_highest_threshold() -> None:
    """Spec 4, steps 2-5: 50 units give 15%, not 5% + 10%."""
    fifty = [line(qty="50", unit_price_kopecks="1990")]
    assert calculate_order_total(fifty) == 101_490


def test_promo_code_beats_tier_discount() -> None:
    """Spec 4, steps 3-4: the bigger percentage wins, the two do not add up."""
    # 5% tier + 15% promo would be 20%; only the 15% promo applies.
    ten = [line(qty="10", unit_price_kopecks="1990")]
    assert calculate_order_total(ten, promo_code="SUMMER15") == 20_298
    # The 15% tier beats the 10% promo instead of adding to it.
    fifty = [line(qty="50", unit_price_kopecks="1990")]
    assert calculate_order_total(fifty, promo_code="WELCOME10") == 101_490


def test_discount_is_capped_at_thirty_percent() -> None:
    """Spec 4, step 5: VIP35 gives 35%, but the cap is 30%. Compare with example 4."""
    big = [line(qty="100", unit_price_kopecks="10000")]
    assert calculate_order_total(big, promo_code="VIP35", shipping_city="spb") == 840_000


def test_delivery_is_charged_for_small_order() -> None:
    """Spec 4, steps 7-10: a city adds SHIPPING_KOPEKS and VAT is charged on it."""
    # Example 3: 84 575 after discount + 49 000 delivery, VAT on the whole 133 575.
    fifty = [line(qty="50", unit_price_kopecks="1990")]
    assert calculate_order_total(fifty, promo_code="WELCOME10", shipping_city="msk") == 160_290


def test_free_delivery_uses_discounted_subtotal() -> None:
    """Spec 4, step 7: the threshold is checked against the sum after the discount."""
    # The subtotal is exactly 500 000, but the 15% tier discount takes it below
    # the threshold, so the delivery is paid for.
    hundred = [line(qty="100", unit_price_kopecks="5000")]
    assert calculate_order_total(hundred, shipping_city="msk") == 568_800


def test_delivery_is_free_exactly_at_the_threshold() -> None:
    """Spec 4, step 7: the comparison is strict, so 500 000 already ships free."""
    at_threshold = [line(unit_price_kopecks="500000")]
    assert calculate_order_total(at_threshold, shipping_city="msk") == 600_000


def test_vat_is_charged_on_the_discounted_sum() -> None:
    """Spec 4, steps 8-10: base = discounted subtotal + delivery."""
    # Example 5: 499 999 + 49 000 delivery, VAT of 20% is taken from 548 999.
    boundary = [line(unit_price_kopecks="499999")]
    assert calculate_order_total(boundary, shipping_city="msk") == 658_799


def test_percentages_are_rounded_half_up() -> None:
    """Spec 1: 10% of 1 055 is 106, not 105 - a leftover half kopeck rounds up."""
    odd = [line(unit_price_kopecks="1055")]
    assert calculate_order_total(odd, promo_code="WELCOME10") == 1_139
