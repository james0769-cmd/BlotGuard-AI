"""Database-backed local authentication and signed access tokens."""

from __future__ import annotations

import re
from typing import Any

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from backend.blotguard.core.config import RuntimeConfig
from backend.blotguard.core.errors import AppError
from backend.blotguard.persistence.repository import AnalysisRepository


USERNAME_PATTERN = re.compile(r"^[\w\u4e00-\u9fff]{3,20}$")


class AuthService:
    def __init__(self, config: RuntimeConfig, repository: AnalysisRepository):
        self.config = config
        self.repository = repository
        self.serializer = URLSafeTimedSerializer(
            config.auth_secret_key,
            salt="blotguard-auth-v1",
        )

    def register(self, username: str, password: str) -> dict[str, Any]:
        if not self.config.auth_registration_enabled:
            raise AppError(
                "REGISTRATION_DISABLED",
                "User registration is disabled",
                403,
            )
        normalized = self._validate_credentials(username, password)
        user = self.repository.create_user(
            normalized,
            generate_password_hash(password),
        )
        return self._session(user)

    def login(self, username: str, password: str) -> dict[str, Any]:
        normalized = str(username or "").strip()
        supplied_password = str(password or "")
        if not normalized or not supplied_password:
            raise AppError(
                "INVALID_CREDENTIALS",
                "Username or password is incorrect",
                401,
            )
        user = self.repository.get_user_by_username(
            normalized, include_password_hash=True
        )
        if (
            user is None
            or not user["active"]
            or not check_password_hash(user["password_hash"], supplied_password)
        ):
            raise AppError(
                "INVALID_CREDENTIALS",
                "Username or password is incorrect",
                401,
            )
        user.pop("password_hash", None)
        return self._session(user)

    def authenticate(self, token: str) -> dict[str, Any]:
        try:
            payload = self.serializer.loads(
                token,
                max_age=self.config.auth_token_ttl_seconds,
            )
            user_id = int(payload["user_id"])
        except SignatureExpired as exc:
            raise AppError(
                "TOKEN_EXPIRED",
                "Access token has expired",
                401,
            ) from exc
        except (BadSignature, KeyError, TypeError, ValueError) as exc:
            raise AppError(
                "INVALID_TOKEN",
                "Access token is invalid",
                401,
            ) from exc

        user = self.repository.get_user_by_id(user_id)
        if user is None or not user["active"]:
            raise AppError(
                "INVALID_TOKEN",
                "Access token is invalid",
                401,
            )
        return user

    def _session(self, user: dict[str, Any]) -> dict[str, Any]:
        token = self.serializer.dumps({"user_id": user["id"]})
        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": self.config.auth_token_ttl_seconds,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "role": user["role"],
            },
        }

    @staticmethod
    def _validate_credentials(username: str, password: str) -> str:
        normalized = str(username or "").strip()
        supplied_password = str(password or "")
        if not USERNAME_PATTERN.fullmatch(normalized):
            raise AppError(
                "INVALID_USERNAME",
                "Username must be 3-20 letters, numbers, underscores, or Chinese characters",
                400,
            )
        if len(supplied_password) < 6:
            raise AppError(
                "WEAK_PASSWORD",
                "Password must contain at least 6 characters",
                400,
            )
        return normalized
