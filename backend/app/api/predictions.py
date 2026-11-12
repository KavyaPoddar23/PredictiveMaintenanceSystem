
from fastapi import APIRouter, HTTPException

from backend.app.schemas.prediction import (
    MachinePredictionResponse,
    ModelStatusResponse
)

from backend.app.services.prediction_service import (
    predict_machine_failure,
    get_model_status,
    get_fleet_predictions,
    get_fleet_summary
)

router = APIRouter(
    prefix="/api/v1",
    tags=["Predictive Maintenance"]
)


@router.get(
    "/predictions/{machine_id}",
    response_model=MachinePredictionResponse
)
def predict_machine(machine_id: str):
    try:
        return predict_machine_failure(machine_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(exc)}"
        )


@router.get(
    "/model/status",
    response_model=ModelStatusResponse
)
def model_status():
    try:
        return get_model_status()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not retrieve model status: {str(exc)}"
        )


@router.get("/fleet/predictions")
def fleet_predictions():
    try:
        predictions = get_fleet_predictions()

        return {
            "total_machines": len(predictions),
            "predictions": predictions
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not retrieve fleet predictions: {str(exc)}"
        )


@router.get("/fleet/summary")
def fleet_summary():
    try:
        return get_fleet_summary()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not retrieve fleet summary: {str(exc)}"
        )
