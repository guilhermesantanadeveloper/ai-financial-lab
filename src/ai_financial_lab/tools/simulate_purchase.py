from decimal import Decimal, ROUND_HALF_UP

from ai_financial_lab.tools.month_summary import get_month_summary

def simulate_purchase(
    amount: float,
    installments: int
) -> dict: 

    if amount < 0:
        raise ValueError("Valor precisa ser maior que 0")

    if installments <= 0:
        raise ValueError("Parcelas precisam ser maiores que 0")

    purchase_amount = Decimal(str(amount))

    monthly_payment = (
        purchase_amount / installments
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    month_summary = get_month_summary()

    current_free_margin = Decimal(
        str(month_summary["free_margin"])
    )

    remaining_margin = (
        current_free_margin - monthly_payment
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    return {
        "purchase_amount": float(purchase_amount),
        "installments": installments,
        "monthly_payment": float(monthly_payment),
        "current_free_margin": float(current_free_margin),
        "remaining_margin": float(remaining_margin),
        "fits_monthly_margin": remaining_margin >= 0,
    }

