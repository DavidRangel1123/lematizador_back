import os
import logging
from typing import Tuple, List, Optional, Any, Dict
import pandas as pd
from fastapi import UploadFile
import ast

logger = logging.getLogger(__name__)


class FileUtils:
    """Utilidades para manejo de archivos y proyectos."""

    supported_extensions = [".xlsx", ".xls", ".csv"]

    def __init__(self, base_path: str = "app/projects"):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    # ==================== PROYECTOS ====================
    def get_project_path(self, project_id: str) -> str:
        """Obtiene la ruta del proyecto y valida que exista."""
        project_path = os.path.join(self.base_path, project_id)
        if not os.path.exists(project_path) or not os.path.isdir(project_path):
            raise ValueError(f"El proyecto '{project_id}' no existe")
        return project_path

    def create_project(self, project_name: str) -> dict:
        """Crea la carpeta del proyecto y los archivos de configuración."""
        project_path = os.path.join(self.base_path, project_name)

        if os.path.exists(project_path):
            raise ValueError(f"El proyecto '{project_name}' ya existe")

        # Crear la carpeta del proyecto
        os.makedirs(project_path, exist_ok=False)

        # Crear los archivos de configuración
        config_files = [
            "correcciones_generales.py",
            "correcciones_indumentaria.py",
            "correcciones_corporal.py",
            "stop_words.py",
            "separaciones.py",
        ]

        for filename in config_files:
            file_path = os.path.join(project_path, filename)
            # Nombre del objeto en mayúsculas sin extensión
            object_name = filename.replace(".py", "").upper()

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"{object_name} = {{\n    \n}}\n")

        return {
            "project_name": project_name,
            "path": project_path,
            "config_files": config_files,
        }

    def list_projects(self) -> List[str]:
        """Lista todos los proyectos ordenados."""
        try:
            projects = [
                item
                for item in os.listdir(self.base_path)
                if os.path.isdir(os.path.join(self.base_path, item))
                and not item.startswith(".")
            ]
            return sorted(projects)
        except PermissionError:
            raise PermissionError("No hay permisos para leer la carpeta de proyectos")

    # ==================== ARCHIVOS ====================
    def get_file_extension(self, filename: str) -> str:
        """Valida y retorna la extensión del archivo."""
        _, ext = os.path.splitext(filename)
        ext = ext.lower()
        if ext not in self.supported_extensions:
            raise ValueError(
                f"Extensión no permitida. Permitidas: {', '.join(self.supported_extensions)}"
            )
        return ext

    def find_file(self, project_id: str, suffix: str = "") -> Tuple[str, str]:
        """
        Busca el archivo del proyecto con el sufijo especificado.
        Retorna (file_path, extension). Lanza FileNotFoundError si no existe.
        """
        project_path = self.get_project_path(project_id)
        base_name = f"{project_id}{suffix}"

        for ext in self.supported_extensions:
            file_path = os.path.join(project_path, f"{base_name}{ext}")
            if os.path.exists(file_path):
                return file_path, ext

        raise FileNotFoundError(
            f"No se encontró archivo para el proyecto '{project_id}' "
            f"con nombre '{base_name}.xlsx' o '{base_name}.csv'"
        )

    async def save_file(
        self,
        project_id: str,
        file: UploadFile,
        suffix: str = "",
        description: Optional[str] = None,
    ) -> dict:
        """Guarda un archivo en el proyecto con el sufijo especificado."""
        project_path = self.get_project_path(project_id)
        extension = self.get_file_extension(file.filename)

        filename = f"{project_id}{suffix}{extension}"
        file_path = os.path.join(project_path, filename)

        if os.path.exists(file_path):
            raise FileExistsError(f"El archivo '{filename}' ya existe en el proyecto")

        content = await file.read()
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        await file.close()

        return {
            "original_filename": file.filename,
            "saved_as": filename,
            "extension": extension,
            "project_id": project_id,
            "file_path": file_path,
            "file_size": os.path.getsize(file_path),
            "description": description,
        }

    def get_vocabulario_file(self, project_id: str, tipo: str) -> str:
        """
        Obtiene la ruta del archivo de vocabulario según el tipo.
        """
        project_path = self.get_project_path(project_id)

        if tipo == "corporal":
            vocab_file = os.path.join(project_path, "vocabulario_corporal.txt")
        else:
            vocab_file = os.path.join(project_path, "vocabulario_indumentaria.txt")

        if not os.path.exists(vocab_file):
            raise FileNotFoundError(
                f"No se encontró el vocabulario para '{tipo}'. "
                f"Asegúrate de haber procesado el proyecto primero."
            )

        return vocab_file

    def read_vocabulario(self, project_id: str, tipo: str) -> List[str]:
        """
        Lee el archivo de vocabulario y retorna la lista de palabras.

        Args:
            project_id: ID del proyecto
            tipo: 'corporal' o 'indumentaria'

        Returns:
            Lista de palabras del vocabulario
        """
        vocab_file = self.get_vocabulario_file(project_id, tipo)

        with open(vocab_file, "r", encoding="utf-8") as f:
            palabras = [line.strip() for line in f if line.strip()]

        return palabras

    def get_vocabulario_info(self, project_id: str, tipo: str) -> dict:
        """
        Obtiene la información del vocabulario (palabras y estadísticas).

        Args:
            project_id: ID del proyecto
            tipo: 'corporal' o 'indumentaria'

        Returns:
            Dict con la información del vocabulario
        """
        palabras = self.read_vocabulario(project_id, tipo)

        return {
            "project_id": project_id,
            "tipo": tipo,
            "total_palabras": len(palabras),
            "palabras": palabras,
        }

    def _read_config_file(self, file_path: str) -> Dict[str, Any]:
        """
        Lee un archivo de configuración Python y retorna el diccionario.
        """
        if not os.path.exists(file_path):
            return {}

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Buscar el diccionario en el contenido
        # Asume que la variable tiene el mismo nombre que el archivo (en mayúsculas)
        import re

        match = re.search(r"(\w+)\s*=\s*({[^}]*})", content, re.DOTALL)
        if match:
            var_name = match.group(1)
            dict_str = match.group(2)
            try:
                return ast.literal_eval(dict_str)
            except:
                return {}
        return {}

    def _write_config_file(
        self, file_path: str, var_name: str, data: Dict[str, str]
    ) -> None:
        """
        Escribe un archivo de configuración Python con el diccionario actualizado.
        """
        # Convertir el diccionario a string con formato legible
        dict_str = "{\n"
        for key, value in sorted(data.items()):
            dict_str += f'    "{key}": "{value}",\n'
        dict_str += "}\n"

        content = f"{var_name} = {dict_str}"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    def add_correccion(
        self, project_id: str, word: str, action: str, correction: str
    ) -> dict:
        """
        Agrega una corrección al archivo correspondiente del proyecto.

        Args:
            project_id: ID del proyecto
            word: Palabra a corregir
            action: Tipo de acción (separacion, stop-word, general, corporal, indumentaria)
            correction: Corrección a aplicar

        Returns:
            Dict con el resultado de la operación
        """
        project_path = self.get_project_path(project_id)

        # Mapeo de acciones a archivos y nombres de variables
        mapping = {
            "separacion": {"file": "separaciones.py", "var_name": "SEPARACIONES"},
            "stop-word": {"file": "stop_words.py", "var_name": "STOP_WORDS"},
            "general": {
                "file": "correcciones_generales.py",
                "var_name": "CORRECCIONES_GENERALES",
            },
            "corporal": {
                "file": "correcciones_corporal.py",
                "var_name": "CORRECCIONES_CORPORAL",
            },
            "indumentaria": {
                "file": "correcciones_indumentaria.py",
                "var_name": "CORRECCIONES_INDUMENTARIA",
            },
        }

        if action not in mapping:
            raise ValueError(f"Acción no válida: {action}")

        config = mapping[action]
        file_path = os.path.join(project_path, config["file"])
        var_name = config["var_name"]

        # Leer el archivo existente o crear diccionario vacío
        current_dict = self._read_config_file(file_path)

        # Agregar o actualizar la corrección
        current_dict[word] = correction

        # Escribir el archivo actualizado
        self._write_config_file(file_path, var_name, current_dict)

        return {
            "project_id": project_id,
            "action": action,
            "word": word,
            "correction": correction,
            "file_updated": config["file"],
        }

    def add_correcciones(
        self, project_id: str, correcciones: List[Dict[str, str]]
    ) -> List[dict]:
        """
        Agrega múltiples correcciones a los archivos correspondientes.

        Args:
            project_id: ID del proyecto
            correcciones: Lista de diccionarios con 'word', 'action', 'correction'

        Returns:
            Lista de resultados por cada corrección
        """
        results = []
        for corr in correcciones:
            result = self.add_correccion(
                project_id, corr["word"], corr["action"], corr["correction"]
            )
            results.append(result)

        return results

    # ==================== DATAFRAMES ====================
    def read_dataframe(self, file_path: str, extension: str) -> pd.DataFrame:
        """Lee archivo Excel o CSV y retorna DataFrame."""
        try:
            if extension in [".xlsx", ".xls"]:
                return pd.read_excel(file_path)
            return pd.read_csv(file_path)
        except Exception as e:
            raise Exception(f"Error al leer archivo: {str(e)}")

    def combine_columns(
        self, df: pd.DataFrame, columns: List[str], new_column_name: str
    ) -> pd.DataFrame:
        """Combina múltiples columnas en una sola."""
        if columns:
            df[new_column_name] = df[columns].apply(
                lambda row: " ".join(row.astype(str).fillna("")), axis=1
            )
        return df

    def save_dataframe(
        self, project_id: str, df: pd.DataFrame, suffix: str = "_lematizable"
    ) -> str:
        """Guarda un DataFrame como CSV en el proyecto."""
        project_path = self.get_project_path(project_id)
        file_path = os.path.join(project_path, f"{project_id}{suffix}.csv")
        df.to_csv(file_path, index=False)
        return file_path
