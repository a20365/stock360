from bson import ObjectId
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from ...models import UserUpdate, UserResponse
from typing import Dict, Any

router = APIRouter()


def get_app() -> FastAPI:
    from ...main import app

    return app


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user",
    description="Atualiza campos de um utilizador existente. Retorna 404 se não encontrado.",
    responses={
        400: {"description": "Invalid User ID format or no fields to update"},
        404: {"description": "User not found"},
    },
)
async def update_user(
    user_id: str, updates: UserUpdate, app: FastAPI = Depends(get_app)
):
    try:
        object_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid User ID format")

    update_data: Dict[str, Any] = updates.dict(exclude_none=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = await app.mongodb["users"].update_one(
        {"_id": object_id}, {"$set": update_data}
    )

    if result.modified_count == 0 and result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    updated_user = await app.mongodb["users"].find_one(
        {"_id": object_id}, {"password": 0}
    )

    if updated_user:
        updated_user["id"] = str(updated_user.pop("_id"))
        return UserResponse(**updated_user)
    else:
        raise HTTPException(status_code=500, detail="Failed to retrieve updated user")
