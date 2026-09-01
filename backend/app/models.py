from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String, primary_key=True, index=True)
    batch_id = Column(String, index=True, nullable=False)
    timestamp = Column(String, nullable=False)  # ISO 8601 UTC
    amount = Column(Float, nullable=False)
    payment_method = Column(String, nullable=False)
    device_id = Column(String, nullable=False)
    is_new_device = Column(Boolean, nullable=False)
    ip_country = Column(String(2), nullable=False)
    billing_country = Column(String(2), nullable=False)
    shipping_country = Column(String(2), nullable=True)  # Nullable for digital goods (EC-1)
    account_age_days = Column(Integer, nullable=False)
    velocity_10min = Column(Integer, nullable=False)
    avg_user_amount = Column(Float, nullable=False)
    anomaly_flag = Column(String, nullable=True)  # EC-6 anomaly flag if velocity unrealistically high
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    score_rel = relationship("Score", back_populates="transaction", uselist=False)
    reason_chain_rel = relationship("ReasonChain", back_populates="transaction", uselist=False)
    cost_rel = relationship("Cost", back_populates="transaction", uselist=False)
    decision_rel = relationship("Decision", back_populates="transaction", uselist=False)


class Score(Base):
    __tablename__ = "scores"

    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), primary_key=True)
    score = Column(Integer, nullable=False)  # 0 to 100
    routing_outcome = Column(String, nullable=False)  # auto-clear, auto-block, review-queue
    decided_by = Column(String, nullable=False)  # rule, llm, degraded_reasoning
    rule_name = Column(String, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    transaction = relationship("Transaction", back_populates="score_rel")


class ReasonChain(Base):
    __tablename__ = "reason_chains"

    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), primary_key=True)
    reason_text = Column(Text, nullable=False)
    referenced_fields = Column(Text, nullable=False)  # JSON serialized string of fields referenced

    transaction = relationship("Transaction", back_populates="reason_chain_rel")


class Cost(Base):
    __tablename__ = "costs"

    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), primary_key=True)
    fp_cost_estimate = Column(Float, nullable=False)  # False positive cost
    fn_cost_estimate = Column(Float, nullable=False)  # False negative cost

    transaction = relationship("Transaction", back_populates="cost_rel")


class Decision(Base):
    __tablename__ = "decisions"

    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), primary_key=True)
    actor_id = Column(String, nullable=False)
    actor_role = Column(String, nullable=False)
    decision = Column(String, nullable=False)  # confirm-block, confirm-clear
    reason_text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    transaction = relationship("Transaction", back_populates="decision_rel")


class AuditLog(Base):
    __tablename__ = "audit_log"

    log_id = Column(String, primary_key=True, default=generate_uuid)
    transaction_id = Column(String, nullable=True)
    event_type = Column(String, nullable=False)  # score, override, config_change
    actor_id = Column(String, nullable=False)
    actor_role = Column(String, nullable=False)
    details = Column(Text, nullable=False)  # JSON blob
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Config(Base):
    __tablename__ = "config"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
    updated_by = Column(String, nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # Analyst, Risk Manager
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class TestLabel(Base):
    """
    DR-1 Ground Truth Table.
    Stored strictly separate from scoring pipelines!
    Used ONLY post-hoc by Metrics Service for precision/recall calculation.
    """
    __tablename__ = "test_labels"

    transaction_id = Column(String, primary_key=True)
    is_fraud = Column(Boolean, nullable=False)
