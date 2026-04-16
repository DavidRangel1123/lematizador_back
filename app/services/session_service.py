import logging
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class ProjectSessionService:
    """
    Servicio singleton para mantener la sesión del proyecto abierto.
    Solo permite un proyecto activo a la vez.
    """

    _instance = None
    _current_project_id: Optional[str] = None
    _current_dataframe: Optional[pd.DataFrame] = None
    _current_file_path: Optional[str] = None
    _current_file_extension: Optional[str] = None
    _current_lematizable_dataframe: Optional[pd.DataFrame] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Inicializar atributos
            cls._instance._current_file_type = None
        return cls._instance

    def open_project(self, project_id: str, file_utils) -> dict:
        """
        Abre un proyecto y carga su DataFrame en memoria.
        Prioriza _procesado si existe, sino _completo.

        Args:
            project_id: ID del proyecto
            file_utils: Instancia de FileUtils para leer archivos

        Returns:
            Dict con información del proyecto abierto
        """
        # Si ya hay un proyecto abierto y es diferente, cerrarlo
        if (
            self._current_project_id is not None
            and self._current_project_id != project_id
        ):
            self.close_project()
            logger.info(f"Proyecto anterior cerrado")

        # Si ya es el mismo proyecto, solo retornar info
        if (
            self._current_project_id == project_id
            and self._current_dataframe is not None
        ):
            logger.info(f"Proyecto '{project_id}' ya estaba abierto")
            return self.get_session_info()

        # Buscar archivo en orden de prioridad: _procesado, luego _completo
        file_path = None
        extension = None
        file_type = None

        try:
            # Intentar abrir _procesado primero
            file_path, extension = file_utils.find_file(project_id, "_procesado")
            file_type = "procesado"
            logger.info(f"Encontrado archivo _procesado para proyecto '{project_id}'")
        except FileNotFoundError:
            try:
                # Si no existe _procesado, abrir _completo
                file_path, extension = file_utils.find_file(project_id, "_completo")
                file_type = "completo"
                logger.info(
                    f"Encontrado archivo _completo para proyecto '{project_id}'"
                )
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"No se encontró archivo _procesado ni _completo para el proyecto '{project_id}'. "
                    f"Asegúrate de haber subido el archivo."
                )

        try:
            # Leer el dataframe
            logger.info(f"Cargando archivo {file_path}...")
            df = file_utils.read_dataframe(file_path, extension)

            # Guardar en memoria
            self._current_project_id = project_id
            self._current_dataframe = df
            self._current_file_path = file_path
            self._current_file_extension = extension
            self._current_file_type = file_type  # Guardar qué tipo de archivo se abrió

            logger.info(
                f"Proyecto '{project_id}' abierto correctamente. "
                f"Tipo: {file_type}, Filas: {len(df)}, Columnas: {len(df.columns)}"
            )

            return self.get_session_info()

        except Exception as e:
            raise Exception(f"Error al abrir proyecto: {str(e)}")

    def close_project(self) -> dict:
        """Cierra el proyecto actual y libera la memoria."""
        if self._current_project_id is not None:
            project_id = self._current_project_id
            self._current_project_id = None
            self._current_dataframe = None
            self._current_file_path = None
            self._current_file_extension = None
            logger.info(f"Proyecto '{project_id}' cerrado")
            return {"closed_project": project_id}

        return {"message": "No hay proyecto abierto"}

    def get_current_dataframe(self) -> pd.DataFrame:
        """Retorna el DataFrame del proyecto actual."""
        if self._current_dataframe is None:
            raise ValueError(
                "No hay ningún proyecto abierto. Usa /open-project primero."
            )
        return self._current_dataframe

    def get_current_project_id(self) -> str:
        """Retorna el ID del proyecto actual."""
        if self._current_project_id is None:
            raise ValueError(
                "No hay ningún proyecto abierto. Usa /open-project primero."
            )
        return self._current_project_id

    def get_session_info(self) -> dict:
        """Retorna información de la sesión actual."""
        if self._current_project_id is None:
            return {
                "is_open": False,
                "project_id": None,
                "message": "No hay proyecto abierto",
            }

        return {
            "is_open": True,
            "project_id": self._current_project_id,
            "file_path": self._current_file_path,
            "file_type": (
                "Excel" if self._current_file_extension in [".xlsx", ".xls"] else "CSV"
            ),
            "file_stage": getattr(
                self, "_current_file_type", "unknown"
            ),  # 'procesado' o 'completo'
            "rows": len(self._current_dataframe),
            "columns": len(self._current_dataframe.columns),
            "column_names": self._current_dataframe.columns.tolist()[:10],
            "total_columns": len(self._current_dataframe.columns),
        }

    def is_open(self) -> bool:
        """Verifica si hay un proyecto abierto."""
        return (
            self._current_project_id is not None and self._current_dataframe is not None
        )

    def get_columns_current(self) -> dict:
        """
        Obtiene las columnas del DataFrame actual (sin leer archivo).
        """
        df = self.get_current_dataframe()

        return {
            "project_id": self._current_project_id,
            "columns": df.columns.tolist(),
            "total_columns": len(df.columns),
        }

    def open_lematizable(self, project_id: str, file_utils) -> dict:
        """
        Abre específicamente el archivo _lematizable de un proyecto.
        """
        # Si ya hay un proyecto abierto y es diferente, cerrarlo
        if (
            self._current_project_id is not None
            and self._current_project_id != project_id
        ):
            self.close_project()

        # Buscar archivo _lematizable
        file_path, extension = file_utils.find_file(project_id, "_lematizable")

        # Leer el dataframe
        df = file_utils.read_dataframe(file_path, extension)

        # Guardar en memoria
        self._current_project_id = project_id
        self._current_lematizable_dataframe = df
        self._current_file_path = file_path
        self._current_file_extension = extension

        return {
            "is_open": True,
            "project_id": project_id,
            "rows": len(df),
            "columns": len(df.columns),
        }

    def get_current_lematizable_dataframe(self) -> pd.DataFrame:
        """Retorna el DataFrame _lematizable del proyecto actual."""
        if self._current_lematizable_dataframe is None:
            raise ValueError("No hay ningún proyecto _lematizable abierto.")
        return self._current_lematizable_dataframe

    def get_project_files_status(self, project_id: str, file_utils) -> dict:
        """
        Verifica qué archivos existen para un proyecto.
        """
        files_status = {"completo": False, "lematizable": False, "procesado": False}

        try:
            file_utils.find_file(project_id, "_completo")
            files_status["completo"] = True
        except FileNotFoundError:
            pass

        try:
            file_utils.find_file(project_id, "_lematizable")
            files_status["lematizable"] = True
        except FileNotFoundError:
            pass

        try:
            file_utils.find_file(project_id, "_procesado")
            files_status["procesado"] = True
        except FileNotFoundError:
            pass

        return {
            "project_id": project_id,
            "files": files_status,
            "has_procesado": files_status["procesado"],
            "has_lematizable": files_status["lematizable"],
            "has_completo": files_status["completo"],
        }

    def search_lemas_in_current(self, tipo: str, lemas: List[str]) -> dict:
        """
        Busca múltiples lemas en el DataFrame actual.

        Args:
            tipo: 'corporal' o 'indumentaria'
            lemas: Lista de palabras a buscar

        Returns:
            Dict con resultados agrupados por lema
        """
        resultados_por_lema = {}
        todos_los_registros = set()

        for lema in lemas:
            try:
                resultado = self.search_lema_in_current(tipo, lema)
                resultados_por_lema[lema] = {
                    "total_encontrados": resultado["total_encontrados"],
                    "registros": resultado["resultados"],
                }
                # Acumular índices de registros únicos
                for registro in resultado["resultados"]:
                    # Usar un identificador único (podría ser el índice original)
                    if hasattr(registro, "index"):
                        todos_los_registros.add(registro.index)
            except Exception as e:
                resultados_por_lema[lema] = {"error": str(e), "total_encontrados": 0}

        return {
            "project_id": self._current_project_id,
            "tipo": tipo,
            "lemas_buscados": lemas,
            "total_lemas": len(lemas),
            "resultados_por_lema": resultados_por_lema,
            "total_registros_unicos": len(todos_los_registros),
        }

    def search_lema_and_get_limpio(self, tipo: str, lema: str) -> dict:
        """
        Busca un lema en la columna {tipo}_lematizado y retorna el {tipo}_limpio.

        Args:
            tipo: 'corporal' o 'indumentaria'
            lema: Palabra a buscar

        Returns:
            Dict con las coincidencias y sus textos limpios
        """
        if self._current_dataframe is None:
            raise ValueError(
                "No hay ningún proyecto abierto. Usa /open-project primero."
            )

        # Validar tipo
        if tipo not in ["corporal", "indumentaria"]:
            raise ValueError(
                f"Tipo no válido: {tipo}. Debe ser 'corporal' o 'indumentaria'"
            )

        # Construir nombres de columnas
        columna_lematizado = f"{tipo}_lematizado"
        columna_limpio = f"{tipo}_limpio"

        # Verificar que las columnas existan
        if columna_lematizado not in self._current_dataframe.columns:
            raise ValueError(
                f"No se encontró la columna '{columna_lematizado}' en el DataFrame. "
                f"Asegúrate de haber procesado el proyecto primero."
            )

        if columna_limpio not in self._current_dataframe.columns:
            raise ValueError(
                f"No se encontró la columna '{columna_limpio}' en el DataFrame."
            )

        # Buscar coincidencias exactas del lema
        mask = self._current_dataframe[columna_lematizado].str.contains(
            rf"\b{lema}\b", na=False, case=False, regex=True
        )

        resultados_df = self._current_dataframe[mask]

        # Extraer solo las columnas relevantes y limpiar valores nan
        resultados = []
        for idx, row in resultados_df.iterrows():
            # Función para limpiar valores nan
            def clean_value(val):
                if pd.isna(val):
                    return None
                if isinstance(val, float) and (np.isnan(val) or np.isinf(val)):
                    return None
                return val

            resultado_item = {
                "index": int(idx) if isinstance(idx, (int, float)) else idx,
                "lematizado": clean_value(row[columna_lematizado]),
                "limpio": clean_value(row[columna_limpio]),
                "texto_original": clean_value(
                    row.get(tipo, None)
                ),  # 'corporal' o 'indumentaria'
            }

            # Limpiar cualquier otro campo que pueda tener nan
            resultado_item = {
                k: ("" if v is None else v) for k, v in resultado_item.items()
            }

            resultados.append(resultado_item)

        return {
            "project_id": self._current_project_id,
            "tipo": tipo,
            "lema_buscado": lema,
            "columna_lematizado": columna_lematizado,
            "columna_limpio": columna_limpio,
            "total_encontrados": len(resultados),
            "resultados": resultados,
        }


# Instancia global del servicio (singleton)
project_session = ProjectSessionService()
