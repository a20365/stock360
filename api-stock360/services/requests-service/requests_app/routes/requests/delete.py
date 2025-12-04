from bson import ObjectId
from ...models import UserInToken
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from starlette import status
from ...routes.requests.utils import get_current_user

router = APIRouter()


def get_app() -> FastAPI:
    from ...main import app

    return app


@router.delete(
    "/{request_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete request",
    description="Elimina uma requisição; apenas o dono ou admin pode eliminar.",
    responses={
        400: {"description": "Invalid Request ID format"},
        403: {"description": "Forbidden"},
    },
)
async def delete_request(
    request_id: str,
    app: FastAPI = Depends(get_app),
    current_user: UserInToken = Depends(get_current_user),
):
    try:
        object_id = ObjectId(request_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Request ID format")

    existing_request = await app.mongodb["requests"].find_one({"_id": object_id})
    if not existing_request:
        return

    is_owner = current_user.sub == existing_request.get("user_id")
    is_admin = current_user.role == "admin"

    if not is_owner and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own requests or require admin privileges.",
        )

    delete_result = await app.mongodb["requests"].delete_one({"_id": object_id})

    if delete_result.deleted_count == 0:
        return

    return
