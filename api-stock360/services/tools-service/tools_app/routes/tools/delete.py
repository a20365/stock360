from bson import ObjectId
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from starlette import status

from ...models import UserInToken
from ...routes.tools.utils import get_current_admin

router = APIRouter()

def get_app() -> FastAPI:
    from ...main import app

    return app

@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete item",
    description="Elimina um item do inventário por ID. Requer papel de administrador.",
    responses={400: {"description": "Invalid Item ID format"}, 403: {"description": "Access denied"}},
)
async def delete_item(
    item_id: str,
    app: FastAPI = Depends(get_app),
    current_admin: UserInToken = Depends(get_current_admin),
):
    if current_admin.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied. Requires 'admin' role.")

    try:
        object_id = ObjectId(item_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Item ID format")

    delete_result = await app.mongodb["inventory"].delete_one({"_id": object_id})

    if delete_result.deleted_count == 0:
        return

    return