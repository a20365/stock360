from datetime import datetime

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from starlette import status

from ...models import Warehouse, WarehouseCreate, UserInToken
from ...routes.warehouses.utils import get_current_admin

router = APIRouter()


def get_app() -> FastAPI:
    from ...main import app

    return app


@router.post(
    "/",
    response_model=Warehouse,
    status_code=status.HTTP_201_CREATED,
    summary="Create warehouse",
    description="Cria um novo armazém. Requer privilégios de administrador.",
    responses={
        400: {"description": "Validation error"},
        500: {"description": "Failed to retrieve created warehouse"},
    },
)
async def create_warehouse(
    warehouse: WarehouseCreate,
    app: FastAPI = Depends(get_app),
    current_admin: UserInToken = Depends(get_current_admin),
):
    new_warehouse_data = warehouse.dict()

    current_time = datetime.utcnow()
    new_warehouse_data["created_at"] = current_time
    new_warehouse_data["updated_at"] = current_time

    insert_result = await app.mongodb["warehouses"].insert_one(new_warehouse_data)

    created_warehouse = await app.mongodb["warehouses"].find_one(
        {"_id": insert_result.inserted_id}
    )

    if created_warehouse:
        created_warehouse["id"] = str(created_warehouse.pop("_id"))
        return Warehouse(**created_warehouse)
    else:
        raise HTTPException(
            status_code=500, detail="Failed to retrieve created warehouse"
        )
