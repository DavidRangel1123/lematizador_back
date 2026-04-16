from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from typing import Optional, Dict, Any
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


class JWTValidator:
    def __init__(self):
        self.public_key = self._load_public_key()
        self.algorithm = settings.JWT_ALGORITHM
        self.expected_issuer = settings.JWT_ISSUER
        self.expected_aud = settings.JWT_AUD

    def _load_public_key(self) -> str:
        try:
            with open(settings.JWT_PUBLIC_KEY_PATH, "r") as key_file:
                return key_file.read()
        except FileNotFoundError:
            logger.error(
                f"Archivo de clave pública no encontrado: {settings.JWT_PUBLIC_KEY_PATH}"
            )
            raise
        except Exception as e:
            logger.error(f"Error al cargar clave pública: {str(e)}")
            raise

    def verify_token(
        self, token: str, required_audience: Optional[str] = None
    ) -> Dict[str, Any]:

        try:
            options = {
                "verify_signature": True,
                "verify_aud": True,
                "verify_iss": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_nbf": True,
            }

            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.algorithm],
                issuer=self.expected_issuer,
                audience=self.expected_aud,
                options=options,
            )

            logger.info(
                f"Token verificado exitosamente para subject: {payload.get('sub')}"
            )

            return payload

        except JWTError as e:
            logger.warning(f"Error de validación JWT: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token inválido: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

        except Exception as e:
            logger.error(f"Error inesperado al verificar token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno al verificar autenticación",
            )


jwt_validator = JWTValidator()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se proporcionó token de autenticación",
        )

    token = credentials.credentials
    payload = jwt_validator.verify_token(token)

    return payload


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Optional[Dict[str, Any]]:

    if not credentials:
        return None

    try:
        token = credentials.credentials
        return jwt_validator.verify_token(token)
    except HTTPException:
        return None
