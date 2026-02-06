import pytest
from fastapi import HTTPException

from app.api.deps.common import get_user_id_from_header
from app.core.settings import settings


def test_dev_auth_bypass_returns_demo_user():
    original = settings.DEV_AUTH_BYPASS
    try:
        settings.DEV_AUTH_BYPASS = True
        assert get_user_id_from_header() == "demo-user-1"
    finally:
        settings.DEV_AUTH_BYPASS = original


def test_dev_header_allowed_in_development():
    original_env = settings.environment
    original_bypass = settings.DEV_AUTH_BYPASS
    try:
        settings.environment = "development"
        settings.DEV_AUTH_BYPASS = False
        assert get_user_id_from_header("alice-dev") == "alice-dev"
    finally:
        settings.environment = original_env
        settings.DEV_AUTH_BYPASS = original_bypass


def test_prod_rejects_without_real_auth():
    original_env = settings.environment
    original_bypass = settings.DEV_AUTH_BYPASS
    try:
        settings.environment = "production"
        settings.DEV_AUTH_BYPASS = False
        with pytest.raises(HTTPException) as exc:
            get_user_id_from_header("bob")
        assert exc.value.status_code == 401
    finally:
        settings.environment = original_env
        settings.DEV_AUTH_BYPASS = original_bypass
