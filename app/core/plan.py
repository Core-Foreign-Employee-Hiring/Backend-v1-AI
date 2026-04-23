from enum import Enum
from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import CurrentUser
from app.core.config import settings


class PlanType(str, Enum):
    """회원 플랜 타입"""

    FREE = "FREE"
    PRO = "PRO"


class MemberPlan(BaseModel):
    """회원 플랜 정보 (Korfit 내부 API 응답에서 추출)"""

    plan_type: PlanType
    end_date: str | None = None


def fetch_member_plan(member_id: str) -> MemberPlan:
    """
    Korfit 내부 API에서 회원 플랜 정보를 조회합니다.

    호출: GET {korfit_api_base_url}/internal/v1/members/{member_id}/plan

    성공 응답 예시:
    {
      "status": 1073741824,
      "success": true,
      "message": "string",
      "data": {
        "planType": "FREE" | "PRO",
        "endDate": "2026-04-22"
      }
    }

    외부 API 호출 실패 / 잘못된 응답은 503 으로 변환합니다.
    """
    url = f"{settings.korfit_api_base_url.rstrip('/')}/internal/v1/members/{member_id}/plan"

    try:
        with httpx.Client(timeout=settings.korfit_api_timeout) as client:
            resp = client.get(url, headers={"accept": "application/json"})
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="플랜 정보를 확인할 수 없습니다 (Korfit API 호출 실패)",
        ) from e

    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="플랜 정보를 확인할 수 없습니다",
        )

    try:
        body = resp.json()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="플랜 정보 응답을 해석할 수 없습니다",
        ) from e

    data = body.get("data") if isinstance(body, dict) else None
    if not body.get("success") or not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="플랜 정보를 확인할 수 없습니다",
        )

    plan_type_raw = str(data.get("planType", "")).upper()
    try:
        plan_type = PlanType(plan_type_raw)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"알 수 없는 플랜 타입입니다: {plan_type_raw or '(empty)'}",
        ) from e

    return MemberPlan(plan_type=plan_type, end_date=data.get("endDate"))


def require_pro_plan(current_user: CurrentUser) -> dict:
    """
    현재 로그인한 사용자가 PRO 플랜인지 확인합니다.

    - FREE 플랜: 403 반환
    - Korfit API 장애/오류: 503 반환
    - PRO 플랜: current_user 를 그대로 반환
    """
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰에 사용자 정보가 없습니다",
        )

    plan = fetch_member_plan(str(user_id))
    if plan.plan_type != PlanType.PRO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="PRO 플랜에서만 사용할 수 있는 기능입니다. 플랜을 업그레이드해주세요.",
        )

    return current_user


ProUser = Annotated[dict, Depends(require_pro_plan)]
