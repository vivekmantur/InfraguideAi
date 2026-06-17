import json
import os
from collections.abc import Awaitable, Callable
from hashlib import sha256
from typing import Any


DEFAULT_TTL_SECONDS = 24 * 60 * 60

try:
    from redis import asyncio as redis_async
except Exception:  # pragma: no cover - optional runtime dependency
    redis_async = None


class RedisPricingCache:

    def __init__(self) -> None:
        self.redis_url = os.getenv(
            "REDIS_URL",
            "redis://localhost:6379/0"
        )
        self.ttl_seconds = int(
            os.getenv(
                "PRICING_CACHE_TTL_SECONDS",
                str(DEFAULT_TTL_SECONDS)
            )
        )
        self.enabled = (
            os.getenv(
                "PRICING_CACHE_ENABLED",
                "true"
            )
            .strip()
            .lower()
            not in {"0", "false", "no"}
        )
        self._client = None
        self._disabled = False

    def _key(
        self,
        namespace: str,
        payload: Any
    ) -> str:

        serialized = json.dumps(
            payload,
            sort_keys=True,
            default=str
        )
        digest = sha256(
            serialized.encode(
                "utf-8"
            )
        ).hexdigest()
        return f"infraguide:pricing:{namespace}:{digest}"

    async def get_or_set(
        self,
        namespace: str,
        payload: Any,
        fetcher: Callable[[], Awaitable[Any]],
        ttl_seconds: int | None = None
    ) -> Any:

        if (
            not self.enabled
            or self._disabled
            or redis_async is None
        ):
            return await fetcher()

        key = self._key(
            namespace,
            payload
        )

        try:
            client = await self._get_client()
            cached = await client.get(
                key
            )

            if cached:
                return json.loads(
                    cached
                )

            value = await fetcher()
            await client.set(
                key,
                json.dumps(
                    value,
                    default=str
                ),
                ex=ttl_seconds or self.ttl_seconds
            )
            return value

        except Exception as ex:
            self._disabled = True
            print(
                "Redis pricing cache unavailable; "
                f"using provider API directly: {ex}"
            )
            return await fetcher()

    async def _get_client(
        self
    ):

        if self._client is None:
            self._client = redis_async.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self._client.ping()

        return self._client


pricing_cache = RedisPricingCache()
