# app/services/auth_service.py
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from app.configs import env, configs

access_token_expire_minutes = configs.get("jwt").get("access_token_expire_minutes")
algorithm = configs.get("jwt").get("algorithm")
secret_key = env.get("SECRET_KEY")


class AuthService:
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        # REMOVE THIS LINE: self.user_service = UserService() # No UserService here

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
            expire = datetime.now(timezone.utc) + expires_delta  # Use timezone.utc
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=access_token_expire_minutes
            )
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
        return encoded_jwt

    def decode_access_token(self, token: str) -> dict:
        """
        Decodes and validates a JWT access token.
        Raises HTTPException if the token is invalid or expired.
        This method should only handle token decoding and basic JWT validation.
        """
        try:
            payload = jwt.decode(token, secret_key, algorithms=[algorithm])
            # You might want to add a check for 'sub' in payload here,
            # but leave the user lookup to get_current_user.
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception:  # Catch any other unexpected errors during decoding
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format",
                headers={"WWW-Authenticate": "Bearer"},
            )
