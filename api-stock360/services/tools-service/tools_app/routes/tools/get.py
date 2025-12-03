from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from starlette import status
from ...models import Item, ItemResponse, UserInToken
from ...routes.tools.utils import get_current_admin

router = APIRouter()


def get_app() -> FastAPI:
    from ...main import app

    return app


@router.get(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Get item",
    description="Recupera um item do inventário por ID.",
    responses={400: {"description": "Invalid Item ID format"}, 404: {"description": "Item not found"}},
)
async def get_item(
    item_id: str,
    app: FastAPI = Depends(get_app)
):
    try:
        object_id = ObjectId(item_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Item ID format")

    item = await app.mongodb["inventory"].find_one({"_id": object_id})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    item["id"] = str(item.pop("_id"))
    return ItemResponse(**item)


@router.get(
    "/",
    response_model=List[ItemResponse],
    summary="List items",
    description="Lista itens do inventário, com filtros opcionais. Requer privilégios de admin para alguns filtros.",
    responses={200: {"description": "Lista de itens retornada"}},
)
async def list_items(
    app: FastAPI = Depends(get_app),
    current_admin: UserInToken = Depends(get_current_admin),
    category_id: Optional[str] = Query(None, description="Filter items by category ID"),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
):
    query_filter = {}

    if category_id:
        query_filter["category_id"] = category_id
    
    query_filter["is_active"] = is_active
    
    items_cursor = app.mongodb["inventory"].find(query_filter).sort("name", 1)
    
    items_list = []
    async for item in items_cursor:
        item["id"] = str(item.pop("_id"))
        items_list.append(ItemResponse(**item))
        
    return items_list