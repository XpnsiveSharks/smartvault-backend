from __future__ import annotations

from typing import Optional

from app.application.ports.user_repository import UserRepository
from app.domain.models.user import User


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self._by_id: dict[str, User] = {}
        self._by_email: dict[str, User] = {}

    def save(self, user: User) -> None:
        self._users[user.email] = user
    
    def clear(self) -> None:
        self._by_id.clear()
        self._by_email.clear()

    def get_by_email(self, email: str) -> Optional[User]:
        return self._by_email.get(email.strip().lower())

    def create(self, user: User) -> User:
        email = user.email.strip().lower()
        self._by_id[user.id] = user
        self._by_email[email] = user
        return user
    
    def get_by_id(self, user_id: str) -> User | None:
        for user in self._users.values():
            if user.id == user_id:
                return user
        return None

    def update_profile(self, user_id: str, full_name: str | None) -> User | None:
        user = self.get_by_id(user_id)
        if not user:
            return None
        
        # Create a copy with the new name (since User is likely frozen/immutable)
        updated_user = replace(user, full_name=full_name)
        self.save(updated_user)
        return updated_user
