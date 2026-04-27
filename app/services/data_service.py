import logging
import traceback
from typing import Optional, List, Tuple
from fastapi import UploadFile
from app.services.nlp_service import NLPService
from app.utils.FileUtils import FileUtils
import spacy
import json
import joblib
import numpy as np
from scipy.sparse import save_npz
import os
from datetime import datetime
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from app.services.session_service import project_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProjectService:
    def __init__(self, base_path: str = "app/projects"):
        self.file_utils = FileUtils(base_path)

        try:
            self.nlp = spacy.load("es_core_news_md")
        except OSError:
            logger.error(
                "Modelo es_core_news_sm no encontrado. Instalar con: python -m spacy download es_core_news_sm"
            )
            raise

    # ==================== PROYECTOS ====================
    def create_project_directory(self, project_name: str) -> dict:
        """Crea la carpeta del proyecto."""
        return self.file_utils.create_project(project_name)

    def list_projects(self) -> List[str]:
        """Lista todos los proyectos ordenados."""
        return self.file_utils.list_projects()

    # ==================== ARCHIVOS ====================
    async def save_project_file(
        self, project_id: str, file: UploadFile, description: Optional[str] = None
    ) -> dict:
        """Guarda el archivo del proyecto con sufijo _completo."""
        try:
            return await self.file_utils.save_file(
                project_id=project_id,
                file=file,
                suffix="_completo",
                description=description,
            )
        except Exception as e:
            logger.error(
                f"Error en save_project_file: {str(e)}\n{traceback.format_exc()}"
            )
            raise

    def get_file_columns(self, project_id: str) -> dict:
        """Obtiene los nombres de las columnas del archivo _completo."""
        return self.file_utils.get_columns(project_id, suffix="_completo")

    def get_vocabulario(self, project_id: str, tipo: str) -> dict:
        """
        Obtiene las palabras del vocabulario según el tipo especificado.
        """
        return self.file_utils.get_vocabulario_info(project_id, tipo)

    # ==================== PROCESAMIENTO ====================
    def process_column_classification(
        self,
        project_id: str,
        corporal_columns: List[str],
        indumentaria_columns: List[str],
    ) -> dict:
        """
        Procesa clasificación de columnas y genera archivo _lematizable.
        Usa el DataFrame abierto en memoria si está disponible.
        """

        # Verificar si el proyecto actual está abierto y coincide
        if (
            project_session.is_open()
            and project_session.get_current_project_id() == project_id
        ):
            # Usar el DataFrame en memoria
            df = project_session.get_current_dataframe()
            logger.info(f"Usando DataFrame en memoria para proyecto '{project_id}'")

            # Obtener extensión del archivo original (para metadata)
            _, extension = self.file_utils.find_file(project_id, "_completo")

        # else:
        #     # Fallback: leer el archivo directamente
        #     logger.warning(
        #         f"Proyecto '{project_id}' no está abierto en memoria. Leyendo archivo directamente..."
        #     )
        #     file_path, extension = self.file_utils.find_file(project_id, "_completo")
        #     df = self.file_utils.read_dataframe(file_path, extension)

        # Validar que todas las columnas existan
        all_columns = corporal_columns + indumentaria_columns
        missing = [col for col in all_columns if col not in df.columns]
        if missing:
            raise ValueError(f"Columnas no encontradas: {missing}")

        # Combinar columnas
        df = self.file_utils.combine_columns(df, corporal_columns, "corporal")
        df = self.file_utils.combine_columns(df, indumentaria_columns, "indumentaria")

        # Seleccionar columnas finales
        final_columns = []
        if corporal_columns:
            final_columns.append("corporal")
        if indumentaria_columns:
            final_columns.append("indumentaria")

        df_final = df[final_columns]

        # Guardar archivo operable
        operable_path = self.file_utils.save_dataframe(
            project_id, df_final, "_lematizable"
        )

        return {
            "project_id": project_id,
            "original_file": f"{project_id}_completo{extension}",
            "operable_file": operable_path,
            "corporal_columns_used": corporal_columns,
            "indumentaria_columns_used": indumentaria_columns,
            "total_rows": len(df_final),
            "new_columns": final_columns,
            "used_memory_cache": project_session.is_open()
            and project_session.get_current_project_id() == project_id,
        }

    def process_and_vectorize(self, project_id: str) -> dict:
        """
        Procesa el archivo _lematizable.csv del proyecto y genera vectorizadores.
        Usa el DataFrame abierto en memoria si está disponible.
        """
        from app.services.session_service import project_session

        # Obtener ruta del proyecto
        project_path = self.file_utils.get_project_path(project_id)

        # Verificar si el proyecto actual está abierto y tiene el archivo _lematizable
        df = None
        used_memory_cache = False

        if (
            project_session.is_open()
            and project_session.get_current_project_id() == project_id
        ):
            # Intentar obtener el DataFrame, pero necesitamos el _lematizable, no el _completo
            # El session_service solo tiene _completo, así que para _lematizable igual toca leerlo
            # O podríamos guardar también _lematizable en sesión si ya fue clasificado
            logger.info(
                f"Proyecto '{project_id}' está abierto, pero _lematizable requiere lectura directa"
            )

        # Buscar archivo _lematizable (siempre toca leerlo porque es un archivo diferente)
        file_path, extension = self.file_utils.find_file(project_id, "_lematizable")

        # Leer dataframe (siempre del archivo, ya que es el archivo procesado)
        df = self.file_utils.read_dataframe(file_path, extension)
        logger.info(f"Leyendo archivo _lematizable: {file_path}")

        # Verificar columnas necesarias
        required_columns = ["corporal", "indumentaria"]
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            raise ValueError(f"El archivo no tiene las columnas requeridas: {missing}")

        try:
            logger.info(f"Creando NLPService con project_path: {project_path}")
            logger.info(f"Tipo de self.nlp: {type(self.nlp)}")

            nlp_service = NLPService(project_path, self.nlp)

            logger.info("NLPService creado exitosamente")

        except Exception as e:
            logger.error(f"Error AL CREAR NLPService: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise ValueError(f"Error al inicializar NLPService: {str(e)}")

        df = nlp_service.clean_nulls(df)

        # Procesar - CON 7 VARIABLES
        (
            df_procesado,
            vec_corporal,
            vec_indumentaria,
            vectores_corporales,
            vectores_indumentaria,
            palabras_corporal,
            palabras_indumentaria,
        ) = nlp_service.procesar_dataframe(df)

        # Guardar dataframe procesado
        procesado_path = self.file_utils.save_dataframe(
            project_id, df_procesado, "_procesado"
        )

        # Guardar vocabulario (archivos .txt)
        vocabulario_paths = nlp_service.guardar_vocabulario(
            palabras_corporal, palabras_indumentaria
        )

        # Guardar modelos (vectorizadores, vectores, metadata)
        modelos_paths = nlp_service.guardar_modelos(
            project_id,
            vec_corporal,
            vec_indumentaria,
            vectores_corporales,
            vectores_indumentaria,
        )

        return {
            "project_id": project_id,
            "procesado_file": procesado_path,
            "vocabulario": vocabulario_paths,
            "modelos": modelos_paths,
            "estadisticas": {
                "documentos_procesados": vectores_corporales.shape[0],
                "corporal_terminos": len(palabras_corporal),
                "indumentaria_terminos": len(palabras_indumentaria),
                "No-Zero Values Corporal": vectores_corporales.nnz,
                "Densidad Matriz Corporal": vectores_corporales.nnz
                / (vectores_corporales.shape[0] * vectores_corporales.shape[1]),
                "No-Zero Values Indumentaria": vectores_indumentaria.nnz,
                "Densidad Matriz Indumentaria": vectores_indumentaria.nnz
                / (vectores_indumentaria.shape[0] * vectores_indumentaria.shape[1]),
            },
            "used_memory_cache": used_memory_cache,
        }

    def add_correcciones(self, project_id: str, correcciones: List[dict]) -> dict:
        """
        Agrega correcciones a los archivos de configuración del proyecto.
        """
        try:
            self.file_utils.add_correcciones(project_id, correcciones)
            return {
                "success": True,
            }

        except Exception as e:
            logger.error(
                f"Error en add_correcciones: {str(e)}\n{traceback.format_exc()}"
            )
            raise

    def guardar_modelos(
        self,
        project_id: str,
        vectorizador_corporal,
        vectorizador_indumentaria,
        vectores_corporales,
        vectores_indumentaria,
    ) -> dict:
        """
        Guarda los vectorizadores, vectores y metadata en la carpeta del proyecto.

        Args:
            project_id: ID del proyecto
            vectorizador_corporal: Vectorizador TF-IDF entrenado para corporal
            vectorizador_indumentaria: Vectorizador TF-IDF entrenado para indumentaria
            vectores_corporales: Matriz dispersa de vectores corporales
            vectores_indumentaria: Matriz dispersa de vectores indumentaria

        Returns:
            Dict con las rutas de los archivos guardados
        """
        project_path = self.get_project_path(project_id)
        modelos_path = os.path.join(project_path, "modelos")

        # Crear carpeta de modelos si no existe
        os.makedirs(modelos_path, exist_ok=True)

        # Guardar vectorizadores
        vectorizador_corporal_path = os.path.join(
            modelos_path, "vectorizador_corporal.joblib"
        )
        vectorizador_indumentaria_path = os.path.join(
            modelos_path, "vectorizador_indumentaria.joblib"
        )

        joblib.dump(vectorizador_corporal, vectorizador_corporal_path)
        joblib.dump(vectorizador_indumentaria, vectorizador_indumentaria_path)

        # Guardar vectores (matrices dispersas)
        vectores_corporales_path = os.path.join(modelos_path, "vectores_corporales.npz")
        vectores_indumentaria_path = os.path.join(
            modelos_path, "vectores_indumentaria.npz"
        )

        save_npz(vectores_corporales_path, vectores_corporales)
        save_npz(vectores_indumentaria_path, vectores_indumentaria)

        # Guardar vocabularios como .npy
        vocabulario_corporal_path = os.path.join(
            modelos_path, "vocabulario_corporal.npy"
        )
        vocabulario_indumentaria_path = os.path.join(
            modelos_path, "vocabulario_indumentaria.npy"
        )

        np.save(
            vocabulario_corporal_path, vectorizador_corporal.get_feature_names_out()
        )
        np.save(
            vocabulario_indumentaria_path,
            vectorizador_indumentaria.get_feature_names_out(),
        )

        # Crear metadata
        stop_words = list(self.config.get("stop_words", {}))

        metadata = {
            "fecha_creacion": datetime.now().isoformat(),
            "project_id": project_id,
            "dimensiones_corporal": vectores_corporales.shape,
            "dimensiones_indumentaria": vectores_indumentaria.shape,
            "n_documentos": vectores_corporales.shape[0],
            "densidad_corporal": vectores_corporales.nnz
            / (vectores_corporales.shape[0] * vectores_corporales.shape[1]),
            "densidad_indumentaria": vectores_indumentaria.nnz
            / (vectores_indumentaria.shape[0] * vectores_indumentaria.shape[1]),
            "max_features": 10000,
            "vectorizador_config": {
                "lowercase": True,
                "stop_words": stop_words,
                "norm": "l2",
                "use_idf": True,
                "smooth_idf": True,
                "sublinear_tf": True,
            },
        }

        # Guardar metadata
        metadata_path = os.path.join(modelos_path, "metadata.joblib")
        joblib.dump(metadata, metadata_path)

        # También guardar metadata como JSON para fácil lectura

        metadata_json_path = os.path.join(modelos_path, "metadata.json")
        # Convertir tuplas a listas para JSON
        metadata_json = metadata.copy()
        metadata_json["dimensiones_corporal"] = list(
            metadata_json["dimensiones_corporal"]
        )
        metadata_json["dimensiones_indumentaria"] = list(
            metadata_json["dimensiones_indumentaria"]
        )

        with open(metadata_json_path, "w", encoding="utf-8") as f:
            json.dump(metadata_json, f, indent=2, ensure_ascii=False)

        return {
            "modelos_path": modelos_path,
            "vectorizador_corporal": vectorizador_corporal_path,
            "vectorizador_indumentaria": vectorizador_indumentaria_path,
            "vectores_corporales": vectores_corporales_path,
            "vectores_indumentaria": vectores_indumentaria_path,
            "vocabulario_corporal": vocabulario_corporal_path,
            "vocabulario_indumentaria": vocabulario_indumentaria_path,
            "metadata": metadata_path,
            "metadata_json": metadata_json_path,
        }
