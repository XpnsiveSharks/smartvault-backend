from __future__ import annotations
from abc import ABC, abstractmethod
from app.domain.models.user import User
from typing import Optional

class UserRepository(ABC):
    @abstractmethod
    def save(self, user: User) -> None:
        raise NotImplementedError
    
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        raise NotImplementedError

    @abstractmethod
    def create(self, user: User) -> User:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, user_id: str) -> User | None:
        raise NotImplementedError

    @abstractmethod
    def update_profile(self, user_id: str, full_name: str | None) -> User | None:
        raise NotImplementedError