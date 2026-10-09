from datetime import datetime, timezone
from typing import Any

from jose import JWTError, jwt
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.common.errors import BusinessError
from app.core.config import get_settings


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise BusinessError(10002, "AUTH_TOKEN_INVALID", "Token 无效或已过期", 401) from exc
    if not payload.get("sub") or not payload.get("jti"):
        raise BusinessError(10002, "AUTH_TOKEN_INVALID", "Token 缺少必要信息", 401)
    exp = payload.get("exp")
    if isinstance(exp, (int, float)) and exp <= datetime.now(timezone.utc).timestamp():
        raise BusinessError(10002, "AUTH_TOKEN_INVALID", "Token 已过期", 401)
    return payload


def get_redis() -> Redis:
    return Redis.from_url(get_settings().redis_url, decode_responses=True)


async def revoke_token(jti: str, user_id: int, ttl_seconds: int) -> None:
    redis = get_redis()
    try:
        await redis.setex(f"revoked:{jti}", max(ttl_seconds, 1), str(user_id))
    finally:
        await redis.aclose()


async def is_token_revoked(jti: str) -> bool:
    redis = get_redis()
    try:
        return bool(await redis.exists(f"revoked:{jti}"))
    finally:
        await redis.aclose()


async def check_login_rate_limit(identifier: str) -> None:
    redis = get_redis()
    try:
        if await redis.exists(f"login:locked:{identifier.strip().lower()}"):
            raise BusinessError(10005, "AUTH_LOGIN_LOCKED", "登录失败次数过多，账号已暂时锁定", 429)
    except RedisError as exc:
        raise BusinessError(90003, "AUTH_RATE_LIMIT_UNAVAILABLE", "登录保护服务暂不可用", 503) from exc
    finally:
        await redis.aclose()


async def record_login_failure(identifier: str) -> None:
    key = f"login:failures:{identifier.strip().lower()}"
    redis = get_redis()
    try:
        failures = await redis.incr(key)
        await redis.expire(key, 3600)
        if failures >= 5:
            await redis.setex(f"login:locked:{identifier.strip().lower()}", 3600, "1")
    finally:
        await redis.aclose()


async def clear_login_failures(identifier: str) -> None:
    redis = get_redis()
    try:
        await redis.delete(f"login:failures:{identifier.strip().lower()}", f"login:locked:{identifier.strip().lower()}")
    finally:
        await redis.aclose()
