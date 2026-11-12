
from typing import Any, Optional

from pydantic import BaseModel, Field


class ImportantFeature(BaseModel):
    feature: str
    observed_value: Optional[float] = None
    global_importance: float


class MachinePredictionResponse(BaseModel):
    machine_id: str
    machine_name: Optional[str] = None
    machine_type: Optional[str] = None
    criticality: Optional[str] = None

    snapshot_timestamp: str
    prediction_timestamp: str

    prediction_horizon_hours: int = 24
    failure_probability: float = Field(ge=0.0, le=1.0)
    risk_level: str

    recommended_action: str
    model_version: str

    important_features: list[ImportantFeature]
    explanation_note: str


class ModelStatusResponse(BaseModel):
    model_loaded: bool
    model_version: str
    prediction_horizon_hours: int
    feature_count: int
    model_type: str
    message: str
