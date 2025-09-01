"""
인증 관련 API 라우터
회원가입, 로그인, 토큰 관리 등의 엔드포인트를 제공합니다.
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.backend.core.config import settings
from app.backend.core.database import get_async_db
from app.backend.models.user import User, UserRole
from app.backend.schemas.auth import (
    UserCreate,
    UserLogin,
    UserResponse,
    LoginResponse,
    Token,
    PasswordChange,
    PasswordStrengthCheck,
    PasswordStrengthResult,
    ApiResponse,
    ErrorResponse
)
from app.backend.services.auth import AuthService
from app.backend.core.security import validate_password_strength

# 라우터 설정
router = APIRouter(prefix="/auth", tags=["인증"])

# Bearer 토큰 스키마
security = HTTPBearer()


async def get_auth_service(db: AsyncSession = Depends(get_async_db)) -> AuthService:
    """인증 서비스 의존성"""
    return AuthService(db)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> User:
    """
    현재 로그인한 사용자를 가져옵니다.
    
    Raises:
        HTTPException: 인증 실패 시
    """
    user = await auth_service.get_current_user_from_token(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 토큰이 유효하지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="비활성화된 사용자입니다."
        )
    
    return user


async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    관리자 권한이 있는 현재 사용자를 가져옵니다.
    
    Raises:
        HTTPException: 관리자 권한이 없는 경우
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다."
        )
    return current_user


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="회원가입",
    description="새 사용자 계정을 생성합니다."
)
async def register(
    user_data: UserCreate,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """
    새 사용자를 등록합니다.
    
    - **email**: 유효한 이메일 주소 (중복 불가)
    - **password**: 8자 이상, 대/소문자, 숫자 포함
    - **name**: 사용자 이름 (2-100자)
    - **role**: 사용자 역할 (기본값: viewer)
    """
    try:
        user = await auth_service.register_user(user_data)
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"❌ 회원가입 오류: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"회원가입 중 오류가 발생했습니다: {str(e)}" if settings.debug else "회원가입 중 오류가 발생했습니다."
        )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="로그인",
    description="이메일과 비밀번호로 로그인합니다."
)
async def login(
    login_data: UserLogin,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """
    사용자 로그인을 처리합니다.
    
    - **email**: 등록된 이메일 주소
    - **password**: 계정 비밀번호
    
    성공 시 사용자 정보와 JWT 토큰을 반환합니다.
    """
    user = await auth_service.authenticate_user(login_data)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 액세스 토큰 생성
    access_token = auth_service.create_access_token_for_user(user)
    
    return LoginResponse(
        user=UserResponse.model_validate(user),
        token=Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.jwt_expiration_minutes * 60
        )
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="현재 사용자 정보",
    description="현재 로그인한 사용자의 정보를 반환합니다."
)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    현재 로그인한 사용자의 정보를 조회합니다.
    
    Bearer 토큰이 필요합니다.
    """
    return UserResponse.model_validate(current_user)


@router.post(
    "/change-password",
    response_model=ApiResponse,
    summary="비밀번호 변경",
    description="현재 사용자의 비밀번호를 변경합니다."
)
async def change_password(
    password_data: PasswordChange,
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """
    현재 사용자의 비밀번호를 변경합니다.
    
    - **current_password**: 현재 비밀번호
    - **new_password**: 새 비밀번호 (8자 이상, 대/소문자, 숫자 포함)
    """
    try:
        success = await auth_service.update_user_password(
            current_user,
            password_data.current_password,
            password_data.new_password
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="현재 비밀번호가 올바르지 않습니다."
            )
        
        return ApiResponse(
            success=True,
            message="비밀번호가 성공적으로 변경되었습니다."
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="비밀번호 변경 중 오류가 발생했습니다."
        )


@router.post(
    "/check-password-strength",
    response_model=PasswordStrengthResult,
    summary="비밀번호 강도 확인",
    description="비밀번호의 강도를 확인합니다."
)
async def check_password_strength(password_data: PasswordStrengthCheck):
    """
    비밀번호의 강도를 확인합니다.
    
    - **password**: 확인할 비밀번호
    
    0-5점의 강도 점수와 개선 사항을 반환합니다.
    """
    result = validate_password_strength(password_data.password)
    
    return PasswordStrengthResult(
        valid=result["valid"],
        score=result["score"],
        errors=result["errors"]
    )


@router.post(
    "/logout",
    response_model=ApiResponse,
    summary="로그아웃",
    description="현재 세션을 종료합니다."
)
async def logout(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    사용자 로그아웃을 처리합니다.
    
    클라이언트에서 토큰을 삭제하도록 안내합니다.
    """
    return ApiResponse(
        success=True,
        message="성공적으로 로그아웃되었습니다. 토큰을 삭제해주세요."
    )


@router.get(
    "/verify-token",
    response_model=UserResponse,
    summary="토큰 검증",
    description="JWT 토큰의 유효성을 검증합니다."
)
async def verify_token(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    JWT 토큰의 유효성을 검증하고 사용자 정보를 반환합니다.
    
    토큰이 유효한 경우 사용자 정보를 반환합니다.
    """
    return UserResponse.model_validate(current_user)


# 관리자 전용 엔드포인트들
@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="사용자 목록 조회 (관리자)",
    description="모든 사용자 목록을 조회합니다. (관리자 권한 필요)"
)
async def get_users(
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """
    모든 사용자 목록을 조회합니다.
    
    관리자 권한이 필요합니다.
    """
    # TODO: 사용자 목록 조회 로직 구현
    # 현재는 빈 목록 반환
    return []


@router.post(
    "/users/{user_id}/deactivate",
    response_model=ApiResponse,
    summary="사용자 비활성화 (관리자)",
    description="특정 사용자를 비활성화합니다. (관리자 권한 필요)"
)
async def deactivate_user(
    user_id: str,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """
    특정 사용자를 비활성화합니다.
    
    관리자 권한이 필요합니다.
    """
    try:
        import uuid
        user_uuid = uuid.UUID(user_id)
        success = await auth_service.deactivate_user(user_uuid)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )
        
        return ApiResponse(
            success=True,
            message="사용자가 비활성화되었습니다."
        )
    
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 사용자 ID입니다."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자 비활성화 중 오류가 발생했습니다."
        )
