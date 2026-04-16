from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
    UploadFile,
    File,
    Form,
    Request,
    Body,
)
from app.core.security import get_current_user
from typing import Dict, Any, List

# from app.services.queries import Queries
from app.db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

# from app.services.vectorizador import VECTORIZADORES
import logging
import traceback

# from app.services.search_service import SearchService
from app.schemas.project import ProjectCreate
from app.schemas.ColumnClassification import ColumnClassification
from app.schemas.vocabulario import VocabularioTipo, VocabularioResponse
from app.schemas.correcciones import CorreccionesList

from app.services.data_service import ProjectService
from app.services.session_service import project_session

router = APIRouter(prefix="/data", tags=["data"])
logger = logging.getLogger(__name__)

# search_service = SearchService(VECTORIZADORES, df=None)
project_service = ProjectService()


@router.post("/create-project", status_code=status.HTTP_201_CREATED)
def create_project(project_data: ProjectCreate):
    try:
        result = project_service.create_project_directory(project_data.project_name)

        return {
            "status": "success",
            "message": "Proyecto creado exitosamente",
            **result,  # Desempaqueta project_name y path
        }

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/list-projects", status_code=status.HTTP_200_OK)
def list_projects():
    print("Estoy antes del Try-Catch")
    try:
        projects = project_service.list_projects()
        return {"projects": projects}

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


logger = logging.getLogger(__name__)


@router.post("/upload-file", status_code=status.HTTP_200_OK)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
):
    try:
        # Obtener los datos del formulario
        form_data = await request.form()

        project_id = form_data.get("project_id")
        description = form_data.get("description")

        if not project_id:
            logger.error("No se recibió project_id")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se recibió project_id en el formulario",
            )

        result = await project_service.save_project_file(
            project_id=project_id, file=file, description=description
        )

        return {
            "status": "success",
            "message": "Archivo guardado correctamente",
            **result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en endpoint upload-file: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno: {str(e)}",
        )


@router.post("/{project_id}/open-project", status_code=status.HTTP_200_OK)
async def open_project(project_id: str):
    """
    Abre un proyecto y carga su DataFrame en memoria.
    Solo permite un proyecto abierto a la vez.
    Si hay otro proyecto abierto, lo cierra automáticamente.
    """
    try:
        result = project_session.open_project(project_id, project_service.file_utils)

        return {
            "status": "success",
            "message": f"Proyecto '{project_id}' abierto correctamente",
            **result,
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error en open-project: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al abrir proyecto: {str(e)}",
        )


@router.post("/close-project", status_code=status.HTTP_200_OK)
async def close_project():
    """
    Cierra el proyecto actual y libera la memoria.
    """
    try:
        result = project_session.close_project()

        return {"status": "success", **result}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al cerrar proyecto: {str(e)}",
        )


@router.get("/columns", status_code=status.HTTP_200_OK)
async def get_columns_from_open_project():
    """
    Obtiene los nombres de las columnas del proyecto actualmente abierto.
    NO lee el archivo, usa el DataFrame en memoria.
    """
    try:
        result = project_session.get_columns_current()

        return {"status": "success", **result}

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener columnas: {str(e)}",
        )


@router.get("/{project_id}/columns", status_code=status.HTTP_200_OK)
async def get_columns(project_id: str):
    try:
        result = project_service.get_file_columns(project_id)

        return {"status": "success", **result}

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# app/routers/projects.py


@router.post("/{project_id}/classify-columns", status_code=status.HTTP_200_OK)
async def classify_columns(project_id: str, classification: ColumnClassification):
    """
    Clasifica las columnas del proyecto y genera archivo _lematizable.
    Recomendado tener el proyecto abierto con /open-project para mejor rendimiento.
    """
    try:
        result = project_service.process_column_classification(
            project_id, classification.corporal, classification.indumentaria
        )

        return {"status": "success", **result}

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error en classify-columns: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al clasificar columnas: {str(e)}",
        )


@router.post("/{project_id}/process")
async def process_project(project_id: str):
    try:
        result = project_service.process_and_vectorize(project_id)
        return {"status": "success", **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{project_id}/vocabulario",
    status_code=status.HTTP_200_OK,
    response_model=VocabularioResponse,
)
async def get_vocabulario(
    project_id: str,
    tipo: str = Query(
        ..., description="Tipo de vocabulario: 'corporal' o 'indumentaria'"
    ),
):
    """
    Devuelve las palabras del vocabulario según el tipo especificado.

    - **corporal**: Vocabulario de la columna corporal
    - **indumentaria**: Vocabulario de la columna indumentaria
    """
    try:
        # Validar tipo con Pydantic
        tipo_validado = VocabularioTipo(tipo=tipo)

        result = project_service.get_vocabulario(project_id, tipo_validado.tipo)

        return {"status": "success", **result}

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener vocabulario: {str(e)}",
        )


@router.post("/{project_id}/correcciones", status_code=status.HTTP_200_OK)
async def add_correcciones(project_id: str, correcciones_data: CorreccionesList):
    """
    Agrega correcciones a los archivos de configuración del proyecto.

    - **separacion**: Va a separaciones.py
    - **stop-word**: Va a stop_words.py
    - **general**: Va a correcciones_generales.py
    - **corporal**: Va a correcciones_corporal.py
    - **indumentaria**: Va a correcciones_indumentaria.py
    """
    try:
        # Convertir Pydantic models a dicts
        correcciones_list = [
            {"word": c.word, "action": c.action, "correction": c.correction}
            for c in correcciones_data.correcciones
        ]

        result = project_service.add_correcciones(project_id, correcciones_list)

        return {"status": "success", **result}

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al agregar correcciones: {str(e)}",
        )


@router.post("/search-lemas", status_code=status.HTTP_200_OK)
async def search_lemas(
    tipo: str = Query(..., description="Tipo: 'corporal' o 'indumentaria'"),
    lemas: List[str] = Body(..., description="Lista de palabras a buscar"),
):
    """
    Busca múltiples lemas en el DataFrame actualmente abierto.
    Retorna resultados agrupados por cada lema.
    """
    try:
        result = project_session.search_lemas_in_current(tipo, lemas)

        return {"status": "success", **result}

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error en search-lemas: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al buscar lemas: {str(e)}",
        )


@router.get("/search-lema-limpio", status_code=status.HTTP_200_OK)
async def search_lema_and_get_limpio(
    tipo: str = Query(..., description="Tipo: 'corporal' o 'indumentaria'"),
    lema: str = Query(..., description="Palabra a buscar", min_length=1),
):
    try:
        logger.info(f"Buscando lema: '{lema}', tipo: '{tipo}'")
        result = project_session.search_lema_and_get_limpio(tipo, lema)
        logger.info(f"Resultado encontrado: {result['total_encontrados']} registros")
        return {"status": "success", **result}

    except ValueError as e:
        logger.error(f"ValueError en search-lema-limpio: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error en search-lema-limpio: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al buscar: {str(e)}",
        )
