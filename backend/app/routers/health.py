"""
Health check endpoint para monitoramento de infraestrutura
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.config import settings
from app.core.logging import logger
from datetime import datetime, timezone
import httpx

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Endpoint de health check completo
    Valida conexões com todos os serviços críticos
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {}
    }
    
    # Check 1: Database
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "PostgreSQL connection OK"
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database error: {str(e)}"
        }
        health_status["status"] = "unhealthy"
        logger.error(f"Health check - Database failed: {e}")
    
    # Check 2: Redis
    try:
        redis = await get_redis()
        await redis.ping()
        health_status["checks"]["redis"] = {
            "status": "healthy",
            "message": "Redis connection OK"
        }
    except Exception as e:
        health_status["checks"]["redis"] = {
            "status": "degraded",
            "message": f"Redis error: {str(e)}"
        }
        if health_status["status"] == "healthy":
            health_status["status"] = "degraded"
        logger.warning(f"Health check - Redis failed: {e}")
    
    # Check 3: OpenAI (opcional - não bloqueia)
    try:
        if settings.OPENAI_API_KEY:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
                )
                if response.status_code == 200:
                    health_status["checks"]["openai"] = {
                        "status": "healthy",
                        "message": "OpenAI API accessible"
                    }
                else:
                    health_status["checks"]["openai"] = {
                        "status": "degraded",
                        "message": f"OpenAI API returned {response.status_code}"
                    }
        else:
            health_status["checks"]["openai"] = {
                "status": "not_configured",
                "message": "OpenAI API key not set"
            }
    except Exception as e:
        health_status["checks"]["openai"] = {
            "status": "degraded",
            "message": f"OpenAI check failed: {str(e)}"
        }
        logger.warning(f"Health check - OpenAI failed: {e}")
    
    # Check 4: Mercado Pago (opcional)
    try:
        if settings.MERCADO_PAGO_ACCESS_TOKEN:
            health_status["checks"]["mercado_pago"] = {
                "status": "configured",
                "message": "Mercado Pago credentials configured"
            }
        else:
            health_status["checks"]["mercado_pago"] = {
                "status": "not_configured",
                "message": "Mercado Pago not configured"
            }
    except Exception as e:
        health_status["checks"]["mercado_pago"] = {
            "status": "unknown",
            "message": str(e)
        }
    
    # Check 5: Twilio (opcional)
    try:
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            health_status["checks"]["twilio"] = {
                "status": "configured",
                "message": "Twilio credentials configured"
            }
        else:
            health_status["checks"]["twilio"] = {
                "status": "not_configured",
                "message": "Twilio not configured"
            }
    except Exception as e:
        health_status["checks"]["twilio"] = {
            "status": "unknown",
            "message": str(e)
        }
    
    return health_status


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness probe para Kubernetes
    Retorna 200 se o serviço está pronto para receber tráfego
    """
    try:
        # Verifica apenas database (crítico)
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"status": "not_ready", "error": str(e)}


@router.get("/live")
async def liveness_check():
    """
    Liveness probe para Kubernetes
    Retorna 200 se o processo está vivo
    """
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}
