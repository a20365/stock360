from datetime import datetime
from typing import Any, Dict
from bson import ObjectId
from fastapi import APIRouter, Depends, FastAPI, HTTPException

from ...models import ItemUpdate, ItemResponse, UserInToken
from ...routes.tools.utils import get_current_admin

router = APIRouter()


def get_app() -> FastAPI:
    from ...main import app

    return app


@router.put(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Update item",
    description="Atualiza um item do inventário. Requer papel de administrador.",
    responses={400: {"description": "Invalid Item ID or no fields"}, 403: {"description": "Access denied"}, 404: {"description": "Item not found"}},
)
async def update_item(
    item_id: str,
    updates: ItemUpdate,
    app: FastAPI = Depends(get_app),
    current_admin: UserInToken = Depends(get_current_admin),
):
    if current_admin.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied. Requires 'admin' role.")
    
    try:
        object_id = ObjectId(item_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Item ID format")

    update_data: Dict[str, Any] = updates.dict(exclude_none=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_data["updated_at"] = datetime.utcnow()

    result = await app.mongodb["inventory"].update_one(
        {"_id": object_id},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")

    updated_item = await app.mongodb["inventory"].find_one({"_id": object_id})

    if updated_item:
        updated_item["id"] = str(updated_item.pop("_id"))
        return ItemResponse(**updated_item)
    else:
        raise HTTPException(status_code=500, detail="Failed to retrieve updated item")