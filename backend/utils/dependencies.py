"""
FastAPI зависимости для аутентификации и авторизации.
"""
from typing import Optional, List

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db
from models.user import User, UserRole
from utils.auth import decode_token


# Схема аутентификации через Bearer токен
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Получение текущего авторизованного пользователя.
    Используется как зависимость в защищённых эндпоинтах.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учётные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:
        raise credentials_exception
    
    return user


def require_roles(allowed_roles: List[UserRole]):
    """
    Фабрика зависимостей для проверки роли пользователя.
    
    Использование:
        @router.get("/admin-only")
        async def admin_endpoint(user = Depends(require_roles([UserRole.ADMINISTRATOR]))):
            ...
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.user_type not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для выполнения операции"
            )
        return current_user
    
    return role_checker


# Готовые зависимости для разных уровней доступа
get_operator_user = require_roles([UserRole.OPERATOR, UserRole.ADMINISTRATOR, UserRole.MANAGER])
get_admin_user = require_roles([UserRole.ADMINISTRATOR, UserRole.MANAGER])
get_manager_user = require_roles([UserRole.MANAGER])

