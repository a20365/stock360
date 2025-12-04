from bson import ObjectId
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from starlette import status

from ...models import UserInToken
from ...routes.warehouses.utils import get_current_admin

router = APIRouter()


def get_app() -> FastAPI:
    from ...main import app

    return app


@router.delete(
    "/{warehouse_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete warehouse",
    description="Elimina um armazém por ID. Requer privilégios de administrador.",
    responses={
        400: {"description": "Invalid Warehouse ID format"},
        403: {"description": "Access denied"},
    },
)
async def delete_warehouse(
    warehouse_id: str,
    app: FastAPI = Depends(get_app),
    current_admin: UserInToken = Depends(get_current_admin),
):
    try:
        object_id = ObjectId(warehouse_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Warehouse ID format")

    delete_result = await app.mongodb["warehouses"].delete_one({"_id": object_id})

    if delete_result.deleted_count == 0:
        return

    return
