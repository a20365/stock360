from fastapi import APIRouter, Depends, FastAPI, HTTPException
from datetime import datetime
from ...models import Request, RequestCreate, UserInToken
from ...routes.requests.utils import get_current_user

router = APIRouter()


def get_app() -> FastAPI:
    from ...main import app

    return app


@router.post(
    "/",
    response_model=Request,
    summary="Create request",
    description="Cria uma nova requisição de material associada ao utilizador autenticado.",
    responses={400: {"description": "Validation error"}, 500: {"description": "Failed to retrieve created request"}},
)
async def create_request(
    request: RequestCreate, 
    app: FastAPI = Depends(get_app),
    current_user: UserInToken = Depends(get_current_user),
):
    new_request_data = request.dict()

    current_time = datetime.utcnow()
    new_request_data["user_id"] = current_user.sub
    new_request_data["request_type"] = "Material"
    new_request_data["status"] = "pending"
    new_request_data["created_at"] = current_time
    new_request_data["updated_at"] = current_time

    insert_result = await app.mongodb["requests"].insert_one(new_request_data)
    
    created_request = await app.mongodb["requests"].find_one({"_id": insert_result.inserted_id})
    
    if created_request:
        created_request["id"] = str(created_request.pop("_id"))
        return Request(**created_request)
    else:
        raise HTTPException(status_code=500, detail="Failed to retrieve created request")