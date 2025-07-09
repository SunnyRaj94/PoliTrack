# app/auth/auth.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.configs import env, configs

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2PasswordBearer for JWT token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


access_token_expire_minutes = configs.get("jwt").get("access_token_expire_minutes")
algorithm = configs.get("jwt").get("algorithm")
secret_key = env.get("SECRET_KEY")


class AuthService:
    def __init__(self):
        pass

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=access_token_expire_minutes)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
        return encoded_jwt

    def decode_access_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, secret_key, algorithms=[algorithm])
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
