from datetime import datetime
from typing import Any, Dict

from bson import ObjectId
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from starlette import status

from ...models import WarehouseUpdate, WarehouseResponse, UserInToken
from ...routes.warehouses.utils import get_current_admin

router = APIRouter()

def get_app() -> FastAPI:
    from ...main import app

    return app

@router.put(
    "/{warehouse_id}",
    response_model=WarehouseResponse,
    summary="Update warehouse",
    description="Atualiza um armazém existente. Requer privilégios de administrador.",
    responses={400: {"description": "Invalid Warehouse ID format or no fields to update"}, 404: {"description": "Warehouse not found"}},
)
async def update_warehouse(
    warehouse_id: str,
    updates: WarehouseUpdate,
    app: FastAPI = Depends(get_app),
    current_admin: UserInToken = Depends(get_current_admin),
):
    try:
        object_id = ObjectId(warehouse_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Warehouse ID format")

    update_data: Dict[str, Any] = updates.dict(exclude_none=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_data["updated_at"] = datetime.utcnow()

    result = await app.mongodb["warehouses"].update_one(
        {"_id": object_id},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    updated_warehouse = await app.mongodb["warehouses"].find_one({"_id": object_id})

    if updated_warehouse:
        updated_warehouse["id"] = str(updated_warehouse.pop("_id"))
        return WarehouseResponse(**updated_warehouse)
    else:
        raise HTTPException(status_code=500, detail="Failed to retrieve updated warehouse")