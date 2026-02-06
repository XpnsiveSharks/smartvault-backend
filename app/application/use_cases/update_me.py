from __future__ import annotations
from app.application.ports.user_repository import UserRepository
from app.domain.models.user import User

class UpdateMe:
    def __init__(self, repo: UserRepository):
        self._repo = repo

    def execute(self, user_id: str, full_name: str | None) -> User | None:
        if full_name:
            full_name = full_name.strip()
        return self._repo.update_profile(user_id, full_name)