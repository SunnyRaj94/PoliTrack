# app/dependencies/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# from typing import Optional # Added to hint Optional for future use if needed

from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.schemas.user import UserLogin  # Import UserLogin schema
from app.models.user import User  # Import User model

# from app.configs import (
#     configs,
#     env,
# )  # Assuming you have a settings file for token generation

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")

auth_service = AuthService()
user_service = UserService()


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Dependency that decodes the JWT token and fetches the current authenticated user.
    Raises HTTPException if the token is invalid or the user is not found/active.
    """
    try:
        payload = auth_service.decode_access_token(token)
        user_email: str = payload.get("sub")
        if user_email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = await user_service.get_user_by_email(user_email)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
            )
        return user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def authenticate_user_dependency(
    user_login: UserLogin,
) -> User:  # <--- CHANGE RETURN TYPE TO User
    """
    Dependency that authenticates a user based on email and password.
    It returns the authenticated User object on success.
    Raises HTTPException on failure.
    """
    user = await user_service.get_user_by_email(user_login.email)
    if not user or not auth_service.verify_password(
        user_login.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    # You might also want to check for is_verified here if it's a requirement for login
    # if not user.is_verified:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST, detail="User not verified"
    #     )

    # IMPORTANT CHANGE: Directly return the User object
    return user


def create_access_token_dependency():  # No change needed here
    """
    Dependency that provides a callable function to create JWT access tokens.
    This allows for easy injection into routes.
    """
    return auth_service.create_access_token
