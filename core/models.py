from pydantic import BaseModel
from typing import Optional

class ExperimentCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    metric: str
    traffic_split: Optional[float] = 0.5

class AssignRequest(BaseModel):
    user_id: str
    experiment_id: str

class EventRequest(BaseModel):
    user_id: str
    experiment_id: str
    event_type: str
    value: Optional[float] = 1.0