from fastapi import APIRouter, HTTPException
from data.data_contract import load_data_contract

router = APIRouter(
    prefix="/configs/data-contract",
    tags=["data-contract"],
)


@router.get("/{version}")
def get_data_contract(version: int):
    try:
        return load_data_contract(version)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
