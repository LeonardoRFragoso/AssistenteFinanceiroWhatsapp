from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.services.auth_service import AuthService
from app.utils.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    auth_service = AuthService(db)
    return await auth_service.register(user_data)


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    from app.utils.security_middleware import login_attempt_tracker
    
    # Verificar se está bloqueado
    if await login_attempt_tracker.is_blocked(credentials.email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again in 15 minutes."
        )
    
    try:
        auth_service = AuthService(db)
        token = await auth_service.login(credentials)
        # Limpar tentativas após login bem-sucedido
        await login_attempt_tracker.clear_attempts(credentials.email)
        return token
    except HTTPException as e:
        # Registrar tentativa falhada
        await login_attempt_tracker.track_attempt(credentials.email)
        raise


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    return current_user


@router.get("/me/is-admin")
async def check_admin_status(
    current_user: User = Depends(get_current_user)
):
    """Check if current user has admin privileges"""
    from app.core.config import settings
    
    admin_emails = getattr(settings, 'ADMIN_EMAILS', '').split(',')
    admin_emails = [email.strip() for email in admin_emails if email.strip()]
    
    is_admin = current_user.email in admin_emails
    
    return {"is_admin": is_admin}
