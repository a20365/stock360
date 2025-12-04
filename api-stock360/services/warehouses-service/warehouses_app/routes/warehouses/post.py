import os
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from starlette import status

from ...models import Warehouse, WarehouseCreate, UserInToken
from ...routes.warehouses.utils import get_current_admin

router = APIRouter()


def get_app() -> FastAPI:
    from ...main import app

    return app


async def _geocode_address(address: str) -> tuple[float, float]:
    """Call external geocoding API to resolve lat/lon from address."""
    api_key = os.getenv("GEOLOCATION_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500, detail="Geocoding API key not configured (GEOCODE_API_KEY)."
        )

    url = "https://geocode.maps.co/search"
    params = {"q": address, "api_key": api_key}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Geocoding service error: {exc.response.status_code}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Failed to reach geocoding service") from exc

    if not data:
        raise HTTPException(status_code=400, detail="Address not found in geocoding service")

    first = data[0]
    try:
        lat = float(first["lat"])
        lon = float(first["lon"])
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="Invalid geocoding response format") from exc

    return lat, lon


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

    location = new_warehouse_data.get("location", {})

    if location.get("address") and (
        location.get("lat") is None or location.get("lon") is None
    ):
        lat, lon = await _geocode_address(location["address"])
        location["lat"] = lat
        location["lon"] = lon
        new_warehouse_data["location"] = location

    if location.get("lat") is None or location.get("lon") is None:
        raise HTTPException(
            status_code=400,
            detail="Latitude/Longitude required or resolvable from address.",
        )

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
