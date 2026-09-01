import pytest
from app.cost_calculator import calculate_transaction_cost

def test_calculate_transaction_cost_standard():
    amount = 1000.0
    fp_cost, fn_cost = calculate_transaction_cost(amount)
    
    # FP cost = 500 + 0.15 * 1000 = 650.0
    assert fp_cost == 650.0
    # FN cost = 1500 + 1000 = 2500.0
    assert fn_cost == 2500.0

def test_br5_invalid_cost_inputs():
    with pytest.raises(ValueError, match="BR-5 VIOLATION"):
        calculate_transaction_cost(amount=-100.0)
