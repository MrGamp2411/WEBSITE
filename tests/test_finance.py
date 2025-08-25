from decimal import Decimal
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from finance import calculate_platform_fee, calculate_payout


def test_platform_fee_calculation():
    subtotal = Decimal('100.00')
    fee = calculate_platform_fee(subtotal)
    assert fee == Decimal('5.00')


def test_payout_calculation():
    subtotal = Decimal('100.00')
    vat = Decimal('7.70')
    fee = calculate_platform_fee(subtotal)
    total = subtotal + vat
    payout = calculate_payout(total, fee)
    assert payout == Decimal('102.70')
