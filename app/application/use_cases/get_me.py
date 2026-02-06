from __future__ import annotations
from app.application.ports.user_repository import UserRepository
from app.domain.models.user import User

class GetMe:
    def __init__(self, repo: UserRepository):
        self._repo = repo

    def execute(self, user_id: str) -> User | None:
        return self._repo.get_by_id(user_id)