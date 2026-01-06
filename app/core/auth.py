from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlmodel import Session

from app.core.config import settings
from app.core.database import get_db

# Bearer 토큰 인증
bearer = HTTPBearer()

# JWT 설정 - HMAC512 알고리즘
ALGORITHM = "HS512"


def verify_token(token: str) -> dict:
    """JWT 토큰 검증 (HMAC512)"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않거나 만료된 토큰입니다",
        ) from e


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
) -> dict:
    """현재 로그인한 사용자 정보 조회 (토큰에서)"""
    payload = verify_token(credentials.credentials)
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰에 사용자 정보가 없습니다",
        )
    
    # 토큰 페이로드 전체를 반환 (필요한 정보가 모두 들어있을 수 있음)
    return payload


# 타입 어노테이션 단축
DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(get_current_user)]
