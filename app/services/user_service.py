# app/services/user_service.py
from typing import List, Optional, Union
from beanie import PydanticObjectId
from datetime import datetime

from app.models.user import User, AuditLogEntry  # Import AuditLogEntry
from app.schemas.user import UserUpdate, ProfileUpdate


class UserService:
    def _handle_id(self, user: User):
        user.id = str(user.id)
        return user

    async def create_user(self, user: User) -> Optional[User]:
        """Creates a new user in the database."""
        try:
            await user.insert()
            return user
        except Exception as e:
            # Log the error for debugging
            print(f"Error creating user: {e}")
            return None

    async def get_user_by_id(self, user_id: PydanticObjectId) -> Optional[User]:
        """Retrieves a user by their ID."""
        return await User.get(user_id)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Retrieves a user by their email address."""
        return await User.find_one(User.email == email)

    async def get_all_users(self, limit: int = 100, skip: int = 0) -> List[User]:
        """Retrieves all users with pagination."""
        all_users = await User.find_all(limit=limit, skip=skip).to_list()
        # print("all users --")
        # print(all_users)

        return [self._handle_id(user) for user in all_users]

    async def update_user(
        self,
        user_id: PydanticObjectId,
        user_update: Union[UserUpdate, ProfileUpdate],
        changer_user_id: PydanticObjectId,
    ) -> Optional[User]:
        """
        Updates an existing user's data and logs changes to contact information.
        changer_user_id: The ID of the user who is performing this update.
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        # Prepare data for update, excluding fields not meant for direct update or handled specially
        update_data = user_update.model_dump(exclude_unset=True)

        # Special handling for password hashing if provided
        if "password" in update_data and update_data["password"]:
            from app.services.auth_service import (
                AuthService,
            )  # Import locally to avoid circular dependency

            auth_service = AuthService()
            update_data["hashed_password"] = auth_service.hash_password(
                update_data.pop("password")
            )

        # --- Audit Logging for Contact Information Changes ---
        audit_entries = []
        fields_to_audit = [
            "email",
            "phone_number",
            "first_name",
            "last_name",
            "profile_picture_url",
        ]

        for field_name in fields_to_audit:
            if (
                field_name in update_data
                and getattr(user, field_name) != update_data[field_name]
            ):
                audit_entries.append(
                    AuditLogEntry(
                        changed_by_user_id=changer_user_id,
                        timestamp=datetime.utcnow(),
                        field_name=field_name,
                        old_value=getattr(user, field_name),
                        new_value=update_data[field_name],
                    )
                )

        # Apply updates to the user document
        await user.set(update_data)

        # Append audit entries to the user's audit_log
        if audit_entries:
            # Use append operation to add to list without overwriting
            # $each allows adding multiple elements to the array
            await user.update({"$push": {"audit_log": {"$each": audit_entries}}})

        return user

    async def delete_user(self, user_id: PydanticObjectId) -> bool:
        """Deletes a user by their ID."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        await user.delete()
        return True
