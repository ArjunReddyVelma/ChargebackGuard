from typing import Dict, Any, Tuple, List, Optional
from app.rule_engine import evaluate_transaction_rules
from app.llm_reasoning import generate_llm_reasoning


# Default threshold configuration per FR-5 / EC-4
DEFAULT_LOW_THRESHOLD = 30
DEFAULT_HIGH_THRESHOLD = 70

def assert_no_label_leakage(tx: Dict[str, Any]):
    """
    DR-1 Enforcement: Asserts that ground truth 'is_fraud' label is NEVER passed into scoring/reasoning.
    """
    if "is_fraud" in tx:
        raise ValueError("CRITICAL DR-1 VIOLATION: Ground truth 'is_fraud' label leaked into scoring pipeline input!")

def assign_routing_outcome(score: int, low_threshold: int = DEFAULT_LOW_THRESHOLD, high_threshold: int = DEFAULT_HIGH_THRESHOLD) -> str:
    """
    Assigns routing outcome based on score thresholds per FR-5 & EC-4.
    EC-4: Score exactly equal to threshold belongs to review-queue:
      - score < low_threshold -> auto-clear
      - low_threshold <= score <= high_threshold -> review-queue
      - score > high_threshold -> auto-block
    """
    if score < low_threshold:
        return "auto-clear"
    elif score <= high_threshold:  # Boundary value == high_threshold belongs to review-queue (EC-4)
        return "review-queue"
    else:
        return "auto-block"

def score_and_route_transaction(
    tx: Dict[str, Any], 
    low_threshold: int = DEFAULT_LOW_THRESHOLD, 
    high_threshold: int = DEFAULT_HIGH_THRESHOLD
) -> Tuple[int, str, str, Optional[str], List[str]]:
    """
    Full scoring pipeline for a single transaction.
    
    Returns:
        (score, routing_outcome, decided_by, rule_name, reason_bullets)
    """
    # 1. DR-1 Assertion
    assert_no_label_leakage(tx)

    # 2. Rule Engine check
    status_tag, rule_score, rule_outcome, rule_name, rule_reasons = evaluate_transaction_rules(tx)

    if status_tag == "rule_decided":
        return (rule_score, rule_outcome, "rule", rule_name, rule_reasons)
    
    # 3. LLM Reasoning Layer for ambiguous cases
    llm_score, llm_reasons, decided_by_tag = generate_llm_reasoning(tx, rule_reasons)
    routing_outcome = assign_routing_outcome(llm_score, low_threshold, high_threshold)

    return (llm_score, routing_outcome, decided_by_tag, None, llm_reasons)

