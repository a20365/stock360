from ...models import User, UserInToken
from ...routes.users.utils import get_current_user
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from starlette import status

router = APIRouter()


def get_app() -> FastAPI:
    from ...main import app

    return app


@router.get(
    "/{user_id}",
    response_model=User,
    summary="Get user",
    description=(
        "Devolve o perfil do utilizador identificado por `user_id`. "
        "O utilizador autenticado só pode aceder ao próprio perfil, exceto admin."
    ),
    responses={
        403: {"description": "Forbidden - access other user's profile"},
        404: {"description": "User not found"},
    },
)
async def get_user(
    user_id: str,
    app: FastAPI = Depends(get_app),
    current_user: UserInToken = Depends(get_current_user),
):
    if current_user.sub != user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own user profile.",
        )

    user = await app.mongodb["users"].find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user["id"] = str(user["_id"])
    return User(**user)
