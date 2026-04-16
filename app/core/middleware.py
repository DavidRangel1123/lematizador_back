from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
import logging

logger = logging.getLogger(__name__)


class AuthLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Solo loggear rutas protegidas
        if request.url.path.startswith("/data"):
            auth_header = request.headers.get("authorization")
            if auth_header:
                logger.info(f"Request autenticado a {request.url.path}")
            else:
                logger.warning(f"Request sin autenticación a {request.url.path}")

        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        response.headers["X-Process-Time"] = str(process_time)
        return response
