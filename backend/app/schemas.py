from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import re

# ISO 3166-1 alpha-2 simple regex
ISO_COUNTRY_REGEX = re.compile(r"^[A-Za-z]{2}$")

class TransactionIngestSchema(BaseModel):
    transaction_id: str
    timestamp: str
    amount: float
    payment_method: str
    device_id: str
    is_new_device: bool
    ip_country: str
    billing_country: str
    shipping_country: Optional[str] = None
    account_age_days: int
    velocity_10min: int
    avg_user_amount: float

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        # VR-1: amount must be > 0
        if v <= 0:
            raise ValueError("INVALID_AMOUNT: Transaction amount must be greater than 0.")
        return round(v, 2)

    @field_validator("ip_country", "billing_country")
    @classmethod
    def validate_required_countries(cls, v):
        # VR-2: ISO country code validation
        if not v or not ISO_COUNTRY_REGEX.match(v.strip()):
            raise ValueError(f"INVALID_COUNTRY_CODE: Country code '{v}' must be a valid 2-letter ISO alpha-2 code.")
        return v.strip().upper()

    @field_validator("shipping_country")
    @classmethod
    def validate_optional_shipping(cls, v):
        # VR-2 / EC-1: Nullable shipping_country allowed for digital goods
        if v is not None and v.strip() != "":
            if not ISO_COUNTRY_REGEX.match(v.strip()):
                raise ValueError(f"INVALID_COUNTRY_CODE: Shipping country code '{v}' must be a valid 2-letter ISO alpha-2 code.")
            return v.strip().upper()
        return None

    @field_validator("account_age_days", "velocity_10min")
    @classmethod
    def validate_non_negative_int(cls, v):
        if v < 0:
            raise ValueError("Value cannot be negative.")
        return v

    @field_validator("avg_user_amount")
    @classmethod
    def validate_avg_user_amount(cls, v):
        if v < 0:
            raise ValueError("avg_user_amount cannot be negative.")
        return round(v, 2)

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v):
        # VR-4: Must be valid ISO datetime and not in future
        try:
            # Handle 'Z' suffix or standard ISO format
            clean_ts = v.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            if dt > now + timedelta(minutes=5):  # allow small clock skew
                raise ValueError("INVALID_TIMESTAMP: Transaction timestamp cannot be in the future.")
            return dt.isoformat()
        except ValueError as e:
            if "INVALID_TIMESTAMP" in str(e):
                raise e
            raise ValueError("INVALID_TIMESTAMP: Unable to parse ISO 8601 timestamp.")


class DecisionSubmitSchema(BaseModel):
    decision: str  # confirm-block, confirm-clear
    reason_text: str

    @field_validator("decision")
    @classmethod
    def validate_decision_enum(cls, v):
        if v not in ["confirm-block", "confirm-clear"]:
            raise ValueError("Decision must be either 'confirm-block' or 'confirm-clear'.")
        return v

    @field_validator("reason_text")
    @classmethod
    def validate_reason_length(cls, v):
        # VR-3: Override reason text must be at least 10 characters after trimming
        trimmed = v.strip() if v else ""
        if len(trimmed) < 10:
            raise ValueError("REASON_TOO_SHORT: Reason text must be at least 10 characters long.")
        return trimmed


class ThresholdConfigSchema(BaseModel):
    low_threshold: int
    high_threshold: int

    @model_validator(mode="after")
    def validate_threshold_bounds(self):
        # VR-5 / BR-6: 0 <= low_threshold < high_threshold <= 100
        low = self.low_threshold
        high = self.high_threshold
        if not (0 <= low < high <= 100):
            raise ValueError("INVALID_THRESHOLD_CONFIG: Thresholds must satisfy 0 <= low_threshold < high_threshold <= 100.")
        return self


class CostConfigSchema(BaseModel):
    fp_cost_base: float
    fn_cost_fee: float

    @model_validator(mode="after")
    def validate_positive_cost(self):
        # BR-5: Cost assumptions must always be strictly > 0
        if self.fp_cost_base <= 0 or self.fn_cost_fee <= 0:
            raise ValueError("INVALID_COST_CONFIG: Cost assumptions must be strictly greater than zero.")
        return self


# Imports needed inside validator
from datetime import timedelta
