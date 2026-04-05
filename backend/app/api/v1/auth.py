import uuid
from datetime import timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...deps import get_db
from ...models.user import User
from ...models.api_key import ApiKey
from ...schemas import auth as auth_schema
from ...utils.crypto import get_password_hash, verify_password, verify_api_key, generate_api_key
from ...utils.errors import AuthenticationError

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user(
    request: Request,
    token: Annotated[Optional[str], Depends(oauth2_scheme)] = None,
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get current user from JWT or API Key.
    """
    # 1. Check for API Key in headers first
    api_key_header = request.headers.get("X-API-KEY")
    if api_key_header:
        # Hashed lookup
        prefix = api_key_header[:16]
        query = select(ApiKey).where(ApiKey.key_prefix == prefix, ApiKey.is_active == True)
        result = await db.execute(query)
        api_key_obj = result.scalar_one_or_none()
        
        if api_key_obj and verify_api_key(api_key_header, api_key_obj.key_hash):
            return api_key_obj.user
            
    # 2. Check for JWT token
    if token:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id: str = payload.get("sub")
            if user_id is None:
                raise AuthenticationError()
        except JWTError:
            raise AuthenticationError()
            
        result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
        user = result.scalar_one_or_none()
        if user is None:
            raise AuthenticationError()
        request.state.user = user
        return user
        
    raise AuthenticationError()


@router.post("/register", response_model=auth_schema.User, status_code=status.HTTP_201_CREATED)
async def register(user_in: auth_schema.UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new user.
    """
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="The user with this email already exists.")
        
    user = User(
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        plan="free"
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=auth_schema.Token)
async def login(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Standard OAuth2 compatible token login.
    """
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=auth_schema.User)
async def read_current_user(current_user: Annotated[User, Depends(get_current_user)]):
    """
    Get current logged in user.
    """
    return current_user


@router.post("/keys", response_model=auth_schema.ApiKeyWithPlain)
async def create_key(
    current_user: Annotated[User, Depends(get_current_user)],
    key_in: auth_schema.ApiKeyCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a new API key.
    """
    plaintext, hashed, prefix = generate_api_key()
    api_key = ApiKey(
        user_id=current_user.id,
        key_hash=hashed,
        key_prefix=prefix,
        name=key_in.name
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    
    # We return the plaintext only once
    result = auth_schema.ApiKeyWithPlain.from_orm(api_key)
    result.plaintext_key = plaintext
    return result
