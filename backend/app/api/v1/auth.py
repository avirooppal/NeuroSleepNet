import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Annotated, Optional

logger = logging.getLogger(__name__)

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
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
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Unified authentication: supports Bearer JWT and Bearer API Keys (nsn_sk_).
    """
    auth_header = request.headers.get("Authorization")
    logger.info(f"Authenticating request. Header: {auth_header[:20] if auth_header else 'None'}...")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        
        # 1. API Key check
        if token.startswith("nsn_"):
            # Check for exact hash match
            from ...utils.crypto import verify_api_key
            # We don't store plain keys, but we store hashes.
            # To avoid scanning all keys, we use the prefix to narrow it down if stored.
            # However, the current model uses key_hash.
            stmt = select(ApiKey).where(ApiKey.is_active == True)
            res = await db.execute(stmt)
            keys = res.scalars().all()
            for k in keys:
                if verify_api_key(token, k.key_hash):
                    # Found it
                    k.last_used_at = datetime.now(timezone.utc)
                    await db.commit()
                    user_stmt = select(User).where(User.id == k.user_id)
                    user_res = await db.execute(user_stmt)
                    return user_res.scalar_one()
            
            raise AuthenticationError("Invalid or expired API Key.")

        # 2. JWT check
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id: str = payload.get("sub")
            if user_id:
                stmt = select(User).where(User.id == uuid.UUID(user_id))
                res = await db.execute(stmt)
                user = res.scalar_one_or_none()
                if user:
                    return user
        except (JWTError, ValueError):
            pass

    # 3. Fallback for Local/Self-Host mode (if enabled)
    # This allows zero-setup for the Docker stack
    if settings.ALLOW_ANONYMOUS_ACCESS:
        result = await db.execute(select(User).where(User.email == "anonymous@nsn.local"))
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                id=uuid.uuid4(),
                email="anonymous@nsn.local",
                plan="pro",
                is_active=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
        return user
        
    raise AuthenticationError("Authentication required. Provide a Bearer API Key or JWT.")



@router.post("/register", response_model=auth_schema.User, status_code=status.HTTP_201_CREATED)
async def register(user_in: auth_schema.UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new user with email + password.
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
    if not user or not user.password_hash or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


# ─── GitHub OAuth ─────────────────────────────────────────────────────────────

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAIL_URL = "https://api.github.com/user/emails"


@router.get("/login")
async def github_login():
    """
    Redirect the browser to GitHub's OAuth authorization page.
    The frontend links to this endpoint directly (login via github button).
    """
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="GitHub OAuth is not configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET."
        )
    redirect_uri = (
        f"{GITHUB_AUTH_URL}"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&scope=user:email"
    )
    return RedirectResponse(url=redirect_uri)


@router.get("/callback")
async def github_callback(code: str, db: AsyncSession = Depends(get_db)):
    """
    GitHub redirects here with ?code=... after the user authorizes.
    We exchange the code for a GitHub access token, fetch the user profile,
    upsert a User row, mint a JWT, then redirect the browser to the frontend
    with ?token=<jwt> — the Navbar picks this up from the URL and stores it
    in localStorage.
    """
    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured.")

    async with httpx.AsyncClient() as client:
        # 1. Exchange code for GitHub access token
        token_resp = await client.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
            },
            timeout=10.0,
        )
        token_data = token_resp.json()
        github_access_token = token_data.get("access_token")
        if not github_access_token:
            raise HTTPException(status_code=400, detail="GitHub did not return an access token. The code may be expired or already used.")

        gh_headers = {
            "Authorization": f"Bearer {github_access_token}",
            "Accept": "application/json",
        }

        # 2. Fetch GitHub user profile
        user_resp = await client.get(GITHUB_USER_URL, headers=gh_headers, timeout=10.0)
        gh_user = user_resp.json()
        github_id: int = gh_user["id"]
        github_login: str = gh_user.get("login", "")
        avatar_url: str = gh_user.get("avatar_url", "")

        # 3. Fetch primary verified email (profile email may be None if hidden)
        email_resp = await client.get(GITHUB_EMAIL_URL, headers=gh_headers, timeout=10.0)
        emails = email_resp.json()
        primary_email: Optional[str] = None
        for e in emails:
            if e.get("primary") and e.get("verified"):
                primary_email = e["email"]
                break
        if not primary_email:
            # Fallback: first verified email
            for e in emails:
                if e.get("verified"):
                    primary_email = e["email"]
                    break
        if not primary_email:
            raise HTTPException(
                status_code=400,
                detail="Your GitHub account has no verified email address. Please add one and try again."
            )

    # 4. Upsert user — look up by github_id first, then by email
    result = await db.execute(select(User).where(User.github_id == github_id))
    user = result.scalar_one_or_none()

    if user is None:
        # Try matching by email (user may have registered with password before)
        result = await db.execute(select(User).where(User.email == primary_email))
        user = result.scalar_one_or_none()
        if user:
            # Link GitHub to the existing account
            user.github_id = github_id
            user.avatar_url = avatar_url
        else:
            # Brand new user via GitHub
            user = User(
                email=primary_email,
                github_id=github_id,
                avatar_url=avatar_url,
                plan="free",
            )
            db.add(user)
    else:
        # Refresh avatar in case it changed
        user.avatar_url = avatar_url

    await db.commit()
    await db.refresh(user)

    # 5. Mint our own JWT and redirect back to the frontend
    access_token = create_access_token(data={"sub": str(user.id)})
    frontend_redirect = f"{settings.FRONTEND_URL}?token={access_token}"
    return RedirectResponse(url=frontend_redirect)


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
