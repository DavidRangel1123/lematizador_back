from fastapi import FastAPI
from app.api.router import router
from app.core.handlers import app_exception_handler, generic_exception_handler
from app.core.exceptions import AppException
from app.core.middleware import AuthLoggingMiddleware
import logging


# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


app = FastAPI(title="IJCF API", version="1.0.0")

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Configuración de CORS
origins = [
    "http://localhost:5173",      # React en desarrollo
    "http://127.0.0.1:5173",     # Alternativa con IP
    # Aquí puedes agregar más orígenes si los necesitas
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # Lista de orígenes permitidos
    allow_credentials=True,         # Permitir cookies/credenciales
    allow_methods=["*"],            # Permitir todos los métodos (GET, POST, etc.)
    allow_headers=["*"],            # Permitir todos los headers
)
app.add_middleware(AuthLoggingMiddleware)

# OBTIENE ROUTER GENERAL
app.include_router(router)

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

@app.get("/")
def root():
    return {"message": "FastAPI is running 🚀"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
