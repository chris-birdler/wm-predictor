from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _create_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    creds_exc = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        uid = int(payload["sub"])
    except (JWTError, KeyError, ValueError) as e:
        raise creds_exc from e
    user = db.get(User, uid)
    if user is None:
        raise creds_exc
    return user


@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(400, "Username already taken")
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(400, "Email already registered")
    user = User(
        username=req.username,
        email=req.email,
        password_hash=pwd_ctx.hash(req.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=_create_token(user.id))


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not pwd_ctx.verify(form.password, user.password_hash):
        raise HTTPException(401, "Bad username or password")
    return TokenResponse(access_token=_create_token(user.id))
