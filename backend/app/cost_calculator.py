from typing import Dict, Any, Tuple

# Configurable cost assumptions (Defaults in INR)
DEFAULT_FP_COST_BASE = 500.0  # Estimated cost of false positive (customer friction + lost revenue margin)
DEFAULT_FN_COST_FEE = 1500.0   # Fixed chargeback penalty fee

def calculate_transaction_cost(
    amount: float, 
    fp_cost_base: float = DEFAULT_FP_COST_BASE, 
    fn_cost_fee: float = DEFAULT_FN_COST_FEE
) -> Tuple[float, float]:
    """
    Computes FP cost and FN cost estimates per FR-6.
    
    FP Cost: Estimated cost if a legitimate transaction is wrongly blocked/delayed.
             (Base friction cost + 15% of transaction value margin)
    FN Cost: Estimated cost if a fraudulent transaction is wrongly cleared.
             (Fixed chargeback processing fee + full transaction amount loss)
    """
    if amount < 0 or fp_cost_base <= 0 or fn_cost_fee <= 0:
        raise ValueError("BR-5 VIOLATION: Cost assumptions and amount must be positive numbers greater than zero.")

    fp_cost = round(fp_cost_base + (0.15 * amount), 2)
    fn_cost = round(fn_cost_fee + amount, 2)

    return (fp_cost, fn_cost)
