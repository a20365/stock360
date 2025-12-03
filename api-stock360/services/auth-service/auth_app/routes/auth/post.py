import httpx
from bson import ObjectId
from fastapi import APIRouter, Depends, FastAPI, HTTPException

from ...models import LoginRequest, TokenResponse, UserCreate, UserResponse
from ...security import create_access_token, hash_password, verify_password

router = APIRouter()


def get_app() -> FastAPI:
    from ...main import app

    return app


@router.post(
    "/register",
    response_model=UserResponse,
    summary="Register user",
    description="Regista um novo utilizador. Se o email já existir, devolve 400.",
    responses={
        400: {"description": "User already exists"},
        500: {"description": "Failed to insert or retrieve user"},
    },
)
async def register(user: UserCreate, app: FastAPI = Depends(get_app)):
    existing = await app.mongodb["users"].find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    new_user = user.dict()
    new_user["password"] = hash_password(new_user["password"])
    new_user["role"] = "user"

    new_user["_id"] = new_user.pop("id", str(ObjectId()))

    result = await app.mongodb["users"].insert_one(new_user)

    if result.inserted_id:
        created = await app.mongodb["users"].find_one({"_id": new_user["_id"]})

        if created:
            created["id"] = str(created["_id"])

            async with httpx.AsyncClient() as client:
                await client.post(
                    "http://users-service:80/users/",
                    json={
                        "id": created["id"],
                        "name": user.name,
                        "email": user.email,
                        "role": "user",
                    },
                )

            return UserResponse(**created)
        else:
            raise Exception("User inserted but failed to retrieve immediately after.")
    else:
        raise Exception("Failed to insert user into the database.")


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login",
    description="Autentica um utilizador e devolve um token JWT quando as credenciais estão corretas.",
    responses={401: {"description": "Invalid credentials"}},
)
async def login(request: LoginRequest, app: FastAPI = Depends(get_app)):
    user = await app.mongodb["users"].find_one({"email": request.email})

    if not user or not verify_password(request.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(data={"sub": user["_id"], "role": user["role"]})

    return {"access_token": token, "token_type": "bearer"}
