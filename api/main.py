from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import (
    init_db, create_experiment, log_assignment,
    log_event, get_experiment, get_all_experiments,
    get_experiment_counts, update_experiment_status
)
from core.stats import assign_variant, calculate_results
from core.models import ExperimentCreate, AssignRequest, EventRequest

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="A/B Testing Platform", lifespan=lifespan)

@app.get("/")
def root():
    return {"status": "running", "message": "A/B Testing Platform API"}

@app.post("/experiments")
def create(payload: ExperimentCreate):
    experiment_id = create_experiment(
        payload.name, payload.description,
        payload.metric, payload.traffic_split
    )
    return {"experiment_id": experiment_id, "status": "created"}

@app.get("/experiments")
def list_experiments():
    return get_all_experiments()

@app.get("/experiments/{experiment_id}")
def get_one(experiment_id: str):
    exp = get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp

@app.post("/assign")
def assign(payload: AssignRequest):
    exp = get_experiment(payload.experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if exp["status"] != "running":
        raise HTTPException(status_code=400, detail="Experiment is not running")

    variant = assign_variant(payload.user_id, payload.experiment_id, exp["traffic_split"])
    log_assignment(payload.user_id, payload.experiment_id, variant)
    return {"user_id": payload.user_id, "variant": variant}

@app.post("/events")
def track(payload: EventRequest):
    exp = get_experiment(payload.experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    variant = assign_variant(payload.user_id, payload.experiment_id, exp["traffic_split"])
    log_event(payload.user_id, payload.experiment_id, variant, payload.event_type, payload.value)
    return {"status": "logged"}

@app.get("/results/{experiment_id}")
def results(experiment_id: str):
    exp = get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    counts = get_experiment_counts(experiment_id, exp["metric"])
    c = counts["control"]
    t = counts["treatment"]

    if c["total"] == 0 or t["total"] == 0:
        return {"message": "Not enough data yet", "counts": counts}

    result = calculate_results(
        c["conversions"], c["total"],
        t["conversions"], t["total"],
        experiment_id=experiment_id
    )
    return {
        "experiment": exp,
        "counts": counts,
        "control_rate": result.control_rate,
        "treatment_rate": result.treatment_rate,
        "relative_lift": result.relative_lift,
        "p_value": result.p_value,
        "confidence_interval": result.confidence_interval,
        "is_significant": bool(result.is_significant),
        "recommended_action": result.recommended_action
    }

@app.post("/experiments/{experiment_id}/stop")
def stop(experiment_id: str):
    exp = get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    update_experiment_status(experiment_id, "stopped")
    return {"status": "stopped"}