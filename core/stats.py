import hashlib
import numpy as np
from scipy import stats
from dataclasses import dataclass
from typing import Optional

@dataclass
class ExperimentResult:
    experiment_id: str
    control_conversions: int
    control_total: int
    treatment_conversions: int
    treatment_total: int
    control_rate: float
    treatment_rate: float
    relative_lift: float
    p_value: float
    confidence_interval: tuple
    is_significant: bool
    recommended_action: str

def assign_variant(user_id: str, experiment_id: str, traffic_split: float = 0.5) -> str:
    """Deterministic assignment — same user always gets same variant."""
    hash_input = f"{user_id}:{experiment_id}".encode()
    hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
    bucket = (hash_value % 10000) / 10000.0
    return "treatment" if bucket < traffic_split else "control"

def calculate_results(
    control_conversions: int,
    control_total: int,
    treatment_conversions: int,
    treatment_total: int,
    experiment_id: str = "",
    alpha: float = 0.05,
) -> ExperimentResult:
    control_rate = control_conversions / control_total if control_total > 0 else 0
    treatment_rate = treatment_conversions / treatment_total if treatment_total > 0 else 0
    relative_lift = ((treatment_rate - control_rate) / control_rate * 100) if control_rate > 0 else 0

    # Manual two-proportion z-test (no statsmodels needed)
    p_pool = (control_conversions + treatment_conversions) / (control_total + treatment_total)
    se_pool = np.sqrt(p_pool * (1 - p_pool) * (1/control_total + 1/treatment_total))
    z_stat = (treatment_rate - control_rate) / se_pool if se_pool > 0 else 0
    p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))

    se = np.sqrt(
        (treatment_rate * (1 - treatment_rate) / treatment_total) +
        (control_rate * (1 - control_rate) / control_total)
    ) if treatment_total > 0 and control_total > 0 else 0

    z_critical = stats.norm.ppf(1 - alpha / 2)
    diff = treatment_rate - control_rate
    ci = (round(diff - z_critical * se, 4), round(diff + z_critical * se, 4))

    is_significant = p_value < alpha

    if is_significant and treatment_rate > control_rate:
        action = "Ship treatment — significant improvement detected"
    elif is_significant and treatment_rate < control_rate:
        action = "Stop — treatment is significantly worse"
    elif control_total + treatment_total < 1000:
        action = "Keep running — not enough data yet"
    else:
        action = "No significant difference — consider stopping"

    return ExperimentResult(
        experiment_id=experiment_id,
        control_conversions=control_conversions,
        control_total=control_total,
        treatment_conversions=treatment_conversions,
        treatment_total=treatment_total,
        control_rate=round(control_rate, 4),
        treatment_rate=round(treatment_rate, 4),
        relative_lift=round(relative_lift, 2),
        p_value=round(p_value, 4),
        confidence_interval=ci,
        is_significant=is_significant,
        recommended_action=action,
    )