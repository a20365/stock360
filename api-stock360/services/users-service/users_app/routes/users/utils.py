import os

from ...models import UserInToken
from ...security import decode_token
from fastapi import Depends, HTTPException, Security
from fastapi.security import (APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer)

USERS_API_KEY = os.getenv("USERS_API_KEY")
oauth2_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    api_key: str = Security(api_key_header),
):
    if api_key and api_key == USERS_API_KEY:
        return UserInToken(sub="api_key_user", role="admin")

    if token:
        payload = decode_token(token.credentials)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return UserInToken(**payload)

    raise HTTPException(status_code=401, detail="Not authenticated")
