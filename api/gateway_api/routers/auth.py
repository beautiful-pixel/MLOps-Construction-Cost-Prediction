from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from services.security import (
    authenticate_user,
    create_access_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):

    user = authenticate_user(
        form_data.username,
        form_data.password
    )

    if not user:
        return {"error": "Invalid credentials"}

    access_token = create_access_token({
        "sub": user["username"],
        "role": user["role"]
    })

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
