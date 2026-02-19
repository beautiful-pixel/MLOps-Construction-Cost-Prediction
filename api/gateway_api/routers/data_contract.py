from fastapi import APIRouter, HTTPException, Depends
from data.data_contract import load_data_contract
from services.security import require_admin

router = APIRouter(
    prefix="/configs/data-contract",
    tags=["data-contract"],
)


@router.get("/{version}")
def get_data_contract(version: int, user=Depends(require_admin)):
    try:
        return load_data_contract(version)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
