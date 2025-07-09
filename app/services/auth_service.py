# app/services/auth_service.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

from app.configs import env, configs
from app.models.user import User  # Import User model for type hinting
from app.services.user_service import (
    UserService,
)  # For user lookup during token validation

access_token_expire_minutes = configs.get("jwt").get("access_token_expire_minutes")
algorithm = configs.get("jwt").get("algorithm")
secret_key = env.get("SECRET_KEY")


class AuthService:
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        # Initialize UserService here if needed for token validation lookup
        self.user_service = UserService()

    def hash_password(self, password: str) -> str:
        """Hashes a plain text password."""
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verifies a plain text password against a hashed password."""
        return self.pwd_context.verify(plain_password, hashed_password)

    def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Creates a JWT access token.
        Args:
            data (dict): The payload to encode in the token (e.g., {"sub": user_email}).
            expires_delta (Optional[timedelta]): Optional timedelta for token expiration.
                                                 If None, uses default from settings.
        Returns:
            str: The encoded JWT token.
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=access_token_expire_minutes)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
        return encoded_jwt

    def decode_access_token(self, token: str) -> dict:
        """
        Decodes and validates a JWT access token.
        Raises HTTPException if the token is invalid or expired.
        """
        try:
            payload = jwt.decode(token, secret_key, algorithms=[algorithm])
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def get_current_user_from_token(self, token: str) -> User:
        """
        Decodes the token, extracts the user email, and fetches the user from the database.
        This is a common dependency for protected routes.
        """
        payload = self.decode_access_token(token)
        user_email: str = payload.get(
            "sub"
        )  # 'sub' is standard for subject (user identifier)
        if user_email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Fetch the user from the database using the UserService
        user = await self.user_service.get_user_by_email(user_email)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Ensure the user is active before returning
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
            )
        return user
