"""Tests for the /health route (api/routes/health.py)."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.exc import ArgumentError
from sqlalchemy.sql.elements import ClauseElement

from api.routes.health import health_check


def make_session():
    """Fake AsyncSession whose execute() mimics SQLAlchemy 2.x: a bare str is rejected."""

    async def execute(statement, *args, **kwargs):
        if not isinstance(statement, ClauseElement):
            raise ArgumentError(
                f"Textual SQL expression {statement!r} should be explicitly "
                f"declared as text({statement!r})"
            )

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=execute)
    return session


@pytest.mark.unit
class TestHealthPostgresProbe:
    """Postgres probe in health_check."""

    @pytest.mark.xfail(
        strict=True,
        reason="issue #61: health probe passes raw 'SELECT 1' string to db.execute()",
    )
    @pytest.mark.asyncio
    async def test_postgres_reported_healthy_when_db_reachable(self):
        """A reachable DB must be reported healthy (Redis patched out of the picture)."""
        session = make_session()
        with patch("redis.Redis") as redis_cls:
            redis_cls.return_value.ping.return_value = True
            with (
                patch("core.config.settings.redis_host", "localhost", create=True),
                patch("core.config.settings.redis_port", 6379, create=True),
            ):
                result = await health_check(db=session)
        assert result["dependencies"]["postgres"] == "healthy"
