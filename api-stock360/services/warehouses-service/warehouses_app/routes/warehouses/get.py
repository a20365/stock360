from typing import List
from bson import ObjectId
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from ...models import Warehouse, WarehouseResponse, UserInToken
from ...routes.warehouses.utils import get_current_admin

router = APIRouter()

def get_app() -> FastAPI:
    from ...main import app

    return app

@router.get(
    "/{warehouse_id}",
    response_model=WarehouseResponse,
    summary="Get warehouse",
    description="Recupera um armazém por ID. Requer privilégios de administrador.",
    responses={400: {"description": "Invalid Warehouse ID format"}, 404: {"description": "Warehouse not found"}},
)
async def get_warehouse(
    warehouse_id: str,
    app: FastAPI = Depends(get_app),
    current_admin: UserInToken = Depends(get_current_admin),
):
    try:
        object_id = ObjectId(warehouse_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Warehouse ID format")

    warehouse = await app.mongodb["warehouses"].find_one({"_id": object_id})
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    warehouse["id"] = str(warehouse.pop("_id"))
    return WarehouseResponse(**warehouse)


@router.get(
    "/",
    response_model=List[WarehouseResponse],
    summary="List warehouses",
    description="Lista todos os armazéns. Requer privilégios de administrador.",
    responses={200: {"description": "Lista de armazéns retornada"}},
)
async def list_warehouses(
    app: FastAPI = Depends(get_app),
    current_admin: UserInToken = Depends(get_current_admin),
):
    warehouses_cursor = app.mongodb["warehouses"].find().sort("name", 1)
    
    warehouses_list = []
    async for warehouse in warehouses_cursor:
        warehouse["id"] = str(warehouse.pop("_id"))
        warehouses_list.append(WarehouseResponse(**warehouse))
        
    return warehouses_list