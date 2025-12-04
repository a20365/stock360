from bson import ObjectId
from ...routes.requests.utils import get_current_user
from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    HTTPException,
    Query,
)
from starlette import status
from ...models import (
    UserInToken,
    RequestResponse,
)
from typing import List, Optional


router = APIRouter()


def get_app() -> FastAPI:
    from ...main import app

    return app


@router.get(
    "/{request_id}",
    response_model=RequestResponse,
    summary="Get request",
    description="Recupera uma requisição pelo seu ID. Apenas o dono ou um admin podem aceder.",
    responses={
        400: {"description": "Invalid Request ID format"},
        403: {"description": "Forbidden"},
        404: {"description": "Request not found"},
    },
)
async def get_request(
    request_id: str,
    app: FastAPI = Depends(get_app),
    current_user: UserInToken = Depends(get_current_user),
):
    try:
        object_id = ObjectId(request_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Request ID format")

    request = await app.mongodb["requests"].find_one({"_id": object_id})
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    is_owner = current_user.sub == request.get("user_id")
    is_admin = current_user.role == "admin"
    if not is_owner and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You can only access your own requests or require admin privileges."
            ),
        )

    request["id"] = str(request.pop("_id"))
    return RequestResponse(**request)


@router.get(
    "/",
    response_model=List[RequestResponse],
    summary="List requests",
    description="Lista requisições. Admins podem ver todas e filtrar por utilizador; utilizadores normais " \
    "veem apenas as suas.",
    responses={200: {"description": "Lista de requisições retornada"}},
)
async def list_requests(
    app: FastAPI = Depends(get_app),
    current_user: UserInToken = Depends(get_current_user),
    user_id: Optional[str] = Query(
        None,
        description=("Filter requests by user ID (admin only)"),
    ),
    status_filter: Optional[str] = Query(
        None,
        description="Filter requests by status",
    ),
):
    query_filter = {}

    if current_user.role != "admin":
        query_filter["user_id"] = current_user.sub
    elif user_id:
        query_filter["user_id"] = user_id

    if status_filter:
        query_filter["status"] = status_filter

    collection = app.mongodb["requests"]
    requests_cursor = collection.find(query_filter).sort("created_at", -1)

    requests_list = []
    async for request in requests_cursor:
        request["id"] = str(request.pop("_id"))
        requests_list.append(RequestResponse(**request))

    return requests_list


@router.get(
    "/date-range/",
    response_model=List[RequestResponse],
    summary="Get requests by date range",
    description="Obtém requisições num intervalo de datas (YYYY-MM-DD). Admins podem ver todas; utilizadores " \
    "apenas as suas.",
    responses={400: {"description": "Invalid date format"}},
)
async def get_requests_by_date_range(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    app: FastAPI = Depends(get_app),
    current_user: UserInToken = Depends(get_current_user),
):
    from datetime import datetime

    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=("Invalid date format. Use YYYY-MM-DD."),
        )

    query_filter = {"created_at": {"$gte": start_dt, "$lte": end_dt}}

    if current_user.role != "admin":
        query_filter["user_id"] = current_user.sub

    collection = app.mongodb["requests"]
    requests_cursor = collection.find(query_filter).sort("created_at", -1)

    requests_list = []
    async for request in requests_cursor:
        request["id"] = str(request.pop("_id"))
        requests_list.append(RequestResponse(**request))

    return requests_list
