
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.utils import decode_jwt_token

security = HTTPBearer()

def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Validates JWT token automatically via HTTPBearer.
    This makes Swagger auto-add Authorization: Bearer <token>
    """
    token = credentials.credentials

    try:
        payload = decode_jwt_token(token)
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
