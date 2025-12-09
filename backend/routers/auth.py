"""
Роутер аутентификации.
Реализует методы login() и logout() из класса User в UML диаграмме.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.user import LoginRequest, Token, UserResponse, UserCreate
from utils.auth import verify_password, get_password_hash, create_access_token
from utils.dependencies import get_current_user, get_admin_user
from models.user import UserRole


router = APIRouter()


@router.post("/login", response_model=Token)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Вход в систему.
    Реализация метода login() из диаграммы классов.
    
    Возвращает JWT токен для последующей авторизации.
    """
    # Ищем пользователя по email
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Создаём токен с информацией о пользователе
    token_data = {
        "sub": user.user_id,
        "email": user.email,
        "user_type": user.user_type.value,
    }
    
    access_token = create_access_token(data=token_data)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            user_type=user.user_type,
            department=user.department,
            access_level=user.access_level,
            role_description=user.role_description,
            created_at=user.created_at,
        )
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """
    Выход из системы.
    Реализация метода logout() из диаграммы классов.
    
    Примечание: при использовании JWT на сервере не хранится состояние сессии,
    поэтому выход реализуется удалением токена на клиенте.
    Эндпоинт нужен для логирования и возможной инвалидации токенов в будущем.
    """
    return {"message": "Успешный выход из системы", "user_id": current_user.user_id}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Получение информации о текущем пользователе."""
    return UserResponse(
        id=current_user.id,
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
        user_type=current_user.user_type,
        department=current_user.department,
        access_level=current_user.access_level,
        role_description=current_user.role_description,
        created_at=current_user.created_at,
    )


@router.get("/users", response_model=list[UserResponse])
async def get_all_users(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Получение списка всех пользователей.
    Реализация метода manageUsers() из класса Administrator.
    Доступно только администраторам.
    """
    users = db.query(User).all()
    return [
        UserResponse(
            id=u.id,
            user_id=u.user_id,
            username=u.username,
            email=u.email,
            user_type=u.user_type,
            department=u.department,
            access_level=u.access_level,
            role_description=u.role_description,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.get("/operators", response_model=list[UserResponse])
async def get_operators(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получение списка операторов (техников) для выбора исполнителя.
    Доступно всем аутентифицированным пользователям.
    """
    users = db.query(User).filter(User.user_type == UserRole.OPERATOR).all()
    return [
        UserResponse(
            id=u.id,
            user_id=u.user_id,
            username=u.username,
            email=u.email,
            user_type=u.user_type,
            department=u.department,
            access_level=u.access_level,
            role_description=u.role_description,
            created_at=u.created_at,
        )
        for u in users
    ]

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Создание нового пользователя.
    Часть метода manageUsers() из класса Administrator.
    Доступно только администраторам.
    """
    # Проверяем уникальность email
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )
    
    import uuid
    new_user = User(
        user_id=f"USR-{str(uuid.uuid4())[:8]}",
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        user_type=user_data.user_type,
        department=user_data.department,
        access_level=user_data.access_level,
        role_description=user_data.role_description,
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return UserResponse(
        id=new_user.id,
        user_id=new_user.user_id,
        username=new_user.username,
        email=new_user.email,
        user_type=new_user.user_type,
        department=new_user.department,
        access_level=new_user.access_level,
        role_description=new_user.role_description,
        created_at=new_user.created_at,
    )

