from datetime import datetime
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from starlette import status
from ...models import Item, ItemCreate, UserInToken
from ...routes.tools.utils import get_current_admin

router = APIRouter()


def get_app() -> FastAPI:
    from ...main import app

    return app


@router.post(
    "/",
    response_model=Item,
    status_code=status.HTTP_201_CREATED,
    summary="Create item",
    description="Cria um novo item de inventário. Requer papel de administrador.",
    responses={
        400: {"description": "Validation error"},
        403: {"description": "Access denied"},
    },
)
async def create_item(
    item: ItemCreate,
    app: FastAPI = Depends(get_app),
    current_admin: UserInToken = Depends(get_current_admin),
):
    if current_admin.role != "admin":
        raise HTTPException(
            status_code=403, detail="Access denied. Requires 'admin' role."
        )

    new_item_data = item.dict()

    current_time = datetime.utcnow()
    new_item_data["created_at"] = current_time
    new_item_data["updated_at"] = current_time

    insert_result = await app.mongodb["inventory"].insert_one(new_item_data)

    created_item = await app.mongodb["inventory"].find_one(
        {"_id": insert_result.inserted_id}
    )

    if created_item:
        created_item["id"] = str(created_item.pop("_id"))
        return Item(**created_item)
    else:
        raise HTTPException(status_code=500, detail="Failed to retrieve created item")
