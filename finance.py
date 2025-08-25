from decimal import Decimal, ROUND_HALF_UP

PLATFORM_FEE_RATE = Decimal('0.05')


def calculate_vat_from_gross(price_gross: Decimal, vat_rate: Decimal) -> Decimal:
    """Return the VAT component from a gross price.

    VAT rate is expressed as a percentage (e.g. Decimal('7.7') for 7.7%).
    The calculation assumes `price_gross` already includes VAT.
    """
    if not vat_rate:
        return Decimal('0.00')
    divisor = Decimal('1.00') + (vat_rate / Decimal('100'))
    net_price = price_gross / divisor
    vat_amount = price_gross - net_price
    return vat_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_platform_fee(subtotal: Decimal) -> Decimal:
    """Compute the platform fee (5% of subtotal)."""
    fee = subtotal * PLATFORM_FEE_RATE
    return fee.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_payout(total_gross: Decimal, platform_fee: Decimal) -> Decimal:
    """Amount due to the bar after deducting the platform fee."""
    payout = total_gross - platform_fee
    return payout.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
