# Owner: Dev B
"""Authentication and role guards.

Mock mode: the user comes from the X-Demo-Role and X-Demo-Institution headers.
Otherwise: a Supabase access token (HS256) in the Authorization header.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import get_args

import jwt
from fastapi import Depends, Header, HTTPException, status

from app.core.config import Settings, get_settings
from app.models.auth import Role, User

ROLES: tuple[str, ...] = get_args(Role)
DEFAULT_DEMO_ROLE: Role = "aicte_admin"
DEMO_USER_IDS: dict[str, str] = {
    # The demo student maps to the first student in the mock fixtures.
    "student": "40000000-0000-4000-8000-000000000001",
}


def demo_user(role: str | None, institution: str | None) -> User:
    role = (role or DEFAULT_DEMO_ROLE).strip()
    if role not in ROLES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Unknown X-Demo-Role '{role}'. Use one of: {ROLES}"
        )
    return User(
        id=DEMO_USER_IDS.get(role, f"demo-{role}"),
        role=role,
        institution_id=institution or None,
        display_name=f"Demo {role.replace('_', ' ')}",
        demo=True,
    )


def _user_from_jwt(authorization: str | None, settings: Settings) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.split(" ", 1)[1]
    # TODO(Dev B): support Supabase asymmetric signing keys via the project JWKS endpoint.
    try:
        claims = jwt.decode(
            token, settings.supabase_jwt_secret, algorithms=["HS256"], audience="authenticated"
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc
    app_meta = claims.get("app_metadata") or {}
    role = app_meta.get("role")
    if role not in ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token has no platform role")
    return User(
        id=claims["sub"],
        role=role,
        institution_id=app_meta.get("institution_id"),
        display_name=claims.get("email"),
        demo=False,
    )


def get_current_user(
    authorization: str | None = Header(default=None),
    x_demo_role: str | None = Header(default=None),
    x_demo_institution: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> User:
    if settings.mock_mode:
        return demo_user(x_demo_role, x_demo_institution)
    return _user_from_jwt(authorization, settings)


def require_roles(*roles: Role) -> Callable[..., User]:
    """Dependency that returns the current user, or 403 if their role is not in ``roles``."""

    def guard(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, f"Role '{user.role}' may not access this resource"
            )
        return user

    return guard
