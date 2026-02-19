from fastapi import APIRouter
from services.system_service import SystemService

router = APIRouter(
    prefix="",
    tags=["system"]
)

@router.get("/health")
def health():
    return {"status": "ok"}

system_service = SystemService()

@router.get("/status")
def get_system_status():
    return system_service.get_status()