from bson import ObjectId
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from typing import Dict, Any
from datetime import datetime
from typing import Any, Dict
from starlette import status
from ...models import RequestUpdate, RequestResponse, UserInToken
from ...routes.requests.utils import get_current_user

router = APIRouter()


def get_app() -> FastAPI:
    from ...main import app

    return app


@router.put(
    "/{request_id}",
    response_model=RequestResponse,
    summary="Update request",
    description="Atualiza uma requisição existente. Só o dono ou admin pode atualizar; apenas admin pode alterar o status.",
    responses={400: {"description": "Invalid Request ID format"}, 403: {"description": "Forbidden"}, 404: {"description": "Request not found"}},
)
async def update_request(
    request_id: str,
    request_update: RequestUpdate,
    app: FastAPI = Depends(get_app),
    current_user: UserInToken = Depends(get_current_user),
):
    try:
        object_id = ObjectId(request_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Request ID format")

    existing_request = await app.mongodb["requests"].find_one({"_id": object_id})
    if not existing_request:
        raise HTTPException(status_code=404, detail="Request not found")

    if current_user.sub != existing_request.get("user_id") and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own requests or require admin privileges.",
        )

    update_data: Dict[str, Any] = request_update.dict(exclude_unset=True)

    if "status" in update_data and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update the status of a request.",
        )

    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await app.mongodb["requests"].update_one(
            {"_id": object_id},
            {"$set": update_data}
        )

    updated_request = await app.mongodb["requests"].find_one({"_id": object_id})
    updated_request["id"] = str(updated_request.pop("_id"))
    return RequestResponse(**updated_request)