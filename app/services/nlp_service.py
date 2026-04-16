import os
import re
import pandas as pd
import importlib.util
import sys
from typing import Dict, List, Tuple, Optional
from unidecode import unidecode
from sklearn.feature_extraction.text import TfidfVectorizer
import logging
import joblib
import numpy as np
from scipy.sparse import save_npz
import json
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class NLPService:
    def __init__(self, project_path: str, nlp_model):
        """
        Inicializa el servicio de NLP para un proyecto específico.

        Args:
            project_path: Ruta de la carpeta del proyecto
            nlp_model: Modelo de spaCy cargado
        """
        self.project_path = project_path
        self.nlp = nlp_model
        self.config = self._load_config_files()

    def _load_config_files(self) -> Dict:
        """Carga los archivos de configuración del proyecto."""
        config = {}

        config_files = {
            "stop_words": "stop_words.py",
            "correcciones_generales": "correcciones_generales.py",
            "correcciones_corporal": "correcciones_corporal.py",
            "correcciones_indumentaria": "correcciones_indumentaria.py",
            "separaciones": "separaciones.py",
        }

        for key, filename in config_files.items():
            file_path = os.path.join(self.project_path, filename)
            if os.path.exists(file_path):
                # Cargar el archivo como módulo
                spec = importlib.util.spec_from_file_location(key, file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Extraer la variable principal
                var_name = key.upper()
                if hasattr(module, var_name):
                    config[key] = getattr(module, var_name)
                else:
                    config[key] = {}
                    logger.warning(f"No se encontró {var_name} en {filename}")
            else:
                config[key] = {}
                logger.warning(f"No existe archivo: {filename}")

        return config

    def _normalizar_diccionario_compuestos(self) -> Dict:
        """Normaliza el diccionario de compuestos."""
        diccionario = self.config.get("separaciones", {})
        normalizado = {}

        for clave_original, valor_correccion in diccionario.items():
            clave_normalizada = unidecode(clave_original.lower())
            normalizado[clave_normalizada] = valor_correccion

        return normalizado

    def limpiar_texto(self, texto, diccionario_compuestos=None) -> str:
        """Limpia el texto y aplica correcciones de compuestos."""
        if pd.isna(texto) or not texto:
            return ""

        texto = str(texto)

        # Limpieza básica
        texto = re.sub(r"<br\s*/?>", " ", texto)
        texto = re.sub(r"\\n", " ", texto)
        texto = re.sub(r"\n", " ", texto)
        texto = re.sub(r"\.-", " ", texto)
        texto = re.sub(r"-", " ", texto)
        texto = re.sub(r"\.", " ", texto)
        texto = re.sub(r"S/D", " ", texto)
        texto = re.sub(r"S/N", " ", texto)
        texto = re.sub(r"SIN DATO", " ", texto)
        # texto = re.sub(r"_x000d", " ", texto)
        texto = re.sub(r"•", " ", texto)
        texto = re.sub(r",", " ", texto)
        texto = re.sub(r"[()]", " ", texto)
        texto = re.sub(r"\s+", " ", texto)

        # Corrección de compuestos
        if diccionario_compuestos is None:
            diccionario_compuestos = self._normalizar_diccionario_compuestos()

        palabras = texto.split()
        palabras_corregidas = []

        for palabra in palabras:
            palabra_normalizada = unidecode(palabra.lower())
            if palabra_normalizada in diccionario_compuestos:
                palabras_corregidas.append(diccionario_compuestos[palabra_normalizada])
            else:
                palabras_corregidas.append(palabra)

        texto = " ".join(palabras_corregidas)
        texto = re.sub(r"\s+", " ", texto).strip()

        return texto

    def procesar_texto_unificado(
        self,
        texto: str,
        tipo_dominio: str = "general",
        aplicar_correcciones: bool = True,
    ) -> str:
        """
        Procesa texto con lematización y correcciones específicas por dominio.

        Args:
            texto: Texto a procesar
            tipo_dominio: 'corporal', 'indumentaria' o 'general'
            aplicar_correcciones: Si aplicar correcciones manuales

        Returns:
            Texto procesado con lemas
        """
        if pd.isna(texto) or not texto:
            return ""

        texto = str(texto)

        # Seleccionar diccionario del dominio
        correcciones_dominio = {}
        if tipo_dominio == "corporal":
            correcciones_dominio = self.config.get("correcciones_corporal", {})
        elif tipo_dominio == "indumentaria":
            correcciones_dominio = self.config.get("correcciones_indumentaria", {})

        # Procesar con spaCy
        doc = self.nlp(texto.lower())
        stop_words = self.config.get("stop_words", {})

        tokens_procesados = []

        for token in doc:
            # Criterios para mantener token
            if (
                not token.is_stop
                and not token.is_punct
                and not token.like_num
                and token.text.lower() not in stop_words
                and len(token.lemma_) >= 2
            ):

                lema = token.lemma_
                texto_original = token.text.lower()

                # Aplicar correcciones manuales
                if aplicar_correcciones:
                    # Correcciones generales
                    correcciones_gral = self.config.get("correcciones_generales", {})
                    if texto_original in correcciones_gral:
                        lema = correcciones_gral[texto_original]
                    elif lema in correcciones_gral:
                        lema = correcciones_gral[lema]

                    # Correcciones específicas del dominio
                    if lema in correcciones_dominio:
                        lema = correcciones_dominio[lema]
                    if texto_original in correcciones_dominio:
                        lema = correcciones_dominio[texto_original]

                tokens_procesados.append(lema)

        resultado = " ".join(tokens_procesados)

        # Eliminar acentos
        resultado = unidecode(resultado)

        return resultado

    def procesar_dataframe(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, TfidfVectorizer, TfidfVectorizer]:
        """
        Procesa el dataframe con las columnas 'corporal' e 'indumentaria'.

        Args:
            df: DataFrame con columnas 'corporal' e 'indumentaria'

        Returns:
            Tuple con (df_procesado, vectorizador_corporal, vectorizador_indumentaria)
        """
        logger.info("Iniciando procesamiento de NLP...")

        # Limpiar textos
        diccionario_compuestos = self._normalizar_diccionario_compuestos()

        logger.info("Aplicando limpieza básica...")
        df["corporal_limpio"] = df["corporal"].apply(
            lambda x: self.limpiar_texto(x, diccionario_compuestos)
        )
        df["indumentaria_limpio"] = df["indumentaria"].apply(
            lambda x: self.limpiar_texto(x, diccionario_compuestos)
        )

        # Lematizar
        logger.info("Aplicando lematización...")
        df["corporal_lematizado"] = df["corporal_limpio"].apply(
            lambda x: self.procesar_texto_unificado(x, tipo_dominio="corporal")
        )
        df["indumentaria_lematizado"] = df["indumentaria_limpio"].apply(
            lambda x: self.procesar_texto_unificado(x, tipo_dominio="indumentaria")
        )

        # Vectorizar
        logger.info("Configurando vectorizadores...")
        stop_words = list(self.config.get("stop_words", {}).keys())

        config_vectorizador = {
            "max_features": 10000,
            "lowercase": True,
            "stop_words": stop_words if stop_words else None,
            "token_pattern": r"(?u)\b[a-zA-Záéíóúñ&]{1,}\b",
            "strip_accents": "unicode",
            "norm": "l2",
            "use_idf": True,
            "smooth_idf": True,
            "sublinear_tf": True,
        }

        vectorizador_corporal = TfidfVectorizer(**config_vectorizador)
        vectorizador_indumentaria = TfidfVectorizer(**config_vectorizador)

        logger.info("Vectorizando textos...")
        vectores_corporales = vectorizador_corporal.fit_transform(
            df["corporal_lematizado"]
        )
        vectores_indumentaria = vectorizador_indumentaria.fit_transform(
            df["indumentaria_lematizado"]
        )

        # Obtener palabras del vocabulario
        palabras_corporal = vectorizador_corporal.get_feature_names_out().tolist()
        palabras_indumentaria = (
            vectorizador_indumentaria.get_feature_names_out().tolist()
        )

        logger.info(
            f"Corporal - Documentos: {vectores_corporales.shape[0]}, Términos: {vectores_corporales.shape[1]}"
        )
        logger.info(
            f"Indumentaria - Documentos: {vectores_indumentaria.shape[0]}, Términos: {vectores_indumentaria.shape[1]}"
        )

        return (
            df,
            vectorizador_corporal,
            vectorizador_indumentaria,
            vectores_corporales,
            vectores_indumentaria,
            palabras_corporal,
            palabras_indumentaria,
        )

    def guardar_vocabulario(
        self, palabras_corporal: List[str], palabras_indumentaria: List[str]
    ) -> Dict[str, str]:
        """
        Guarda las palabras del vectorizador en un archivo.
        """
        logger.info("Guardando vocabularios...")

        # Guardar vocabulario corporal
        corporal_path = os.path.join(self.project_path, "vocabulario_corporal.txt")
        with open(corporal_path, "w", encoding="utf-8") as f:
            for palabra in palabras_corporal:
                f.write(f"{palabra}\n")
        logger.info(f"Vocabulario corporal guardado: {corporal_path}")

        # Guardar vocabulario indumentaria
        indumentaria_path = os.path.join(
            self.project_path, "vocabulario_indumentaria.txt"
        )
        with open(indumentaria_path, "w", encoding="utf-8") as f:
            for palabra in palabras_indumentaria:
                f.write(f"{palabra}\n")
        logger.info(f"Vocabulario indumentaria guardado: {indumentaria_path}")

        # Guardar vocabulario completo (combinado)
        completo_path = os.path.join(self.project_path, "vocabulario_completo.txt")
        with open(completo_path, "w", encoding="utf-8") as f:
            f.write("=== VOCABULARIO CORPORAL ===\n")
            for palabra in palabras_corporal:
                f.write(f"{palabra}\n")
            f.write("\n=== VOCABULARIO INDUMENTARIA ===\n")
            for palabra in palabras_indumentaria:
                f.write(f"{palabra}\n")
        logger.info(f"Vocabulario completo guardado: {completo_path}")

        return {
            "corporal": corporal_path,
            "indumentaria": indumentaria_path,
            "completo": completo_path,
            "total_palabras": len(palabras_corporal) + len(palabras_indumentaria),
        }

    def get_project_path(self, project_id: str) -> str:
        """Obtiene la ruta del proyecto."""
        return self.project_path

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

        logger.info("Guardando modelos...")

        project_path = self.project_path  # Usar la ruta del proyecto del NLPService
        modelos_path = os.path.join(project_path, "modelos")

        # Crear carpeta de modelos si no existe
        os.makedirs(modelos_path, exist_ok=True)
        logger.info(f"Carpeta de modelos creada: {modelos_path}")

        # Guardar vectorizadores
        logger.info("Guardando vectorizadores...")
        vectorizador_corporal_path = os.path.join(
            modelos_path, "vectorizador_corporal.joblib"
        )
        vectorizador_indumentaria_path = os.path.join(
            modelos_path, "vectorizador_indumentaria.joblib"
        )

        joblib.dump(vectorizador_corporal, vectorizador_corporal_path)
        joblib.dump(vectorizador_indumentaria, vectorizador_indumentaria_path)
        logger.info("Vectorizadores guardados")

        # Guardar vectores (matrices dispersas)
        logger.info("Guardando vectores...")
        vectores_corporales_path = os.path.join(modelos_path, "vectores_corporales.npz")
        vectores_indumentaria_path = os.path.join(
            modelos_path, "vectores_indumentaria.npz"
        )

        save_npz(vectores_corporales_path, vectores_corporales)
        save_npz(vectores_indumentaria_path, vectores_indumentaria)
        logger.info("Vectores guardados")

        # Guardar vocabularios como .npy
        logger.info("Guardando vocabularios .npy...")
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
        logger.info("Vocabularios .npy guardados")

        # Obtener stop words de la configuración
        stop_words = list(self.config.get("stop_words", {}).keys())

        # Crear metadata
        metadata = {
            "fecha_creacion": datetime.now().isoformat(),
            "project_id": project_id,
            "dimensiones_corporal": list(vectores_corporales.shape),
            "dimensiones_indumentaria": list(vectores_indumentaria.shape),
            "n_documentos": vectores_corporales.shape[0],
            "densidad_corporal": float(
                vectores_corporales.nnz
                / (vectores_corporales.shape[0] * vectores_corporales.shape[1])
            ),
            "densidad_indumentaria": float(
                vectores_indumentaria.nnz
                / (vectores_indumentaria.shape[0] * vectores_indumentaria.shape[1])
            ),
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
        logger.info("Guardando metadata...")
        metadata_path = os.path.join(modelos_path, "metadata.joblib")
        joblib.dump(metadata, metadata_path)

        # También guardar metadata como JSON para fácil lectura
        metadata_json_path = os.path.join(modelos_path, "metadata.json")
        with open(metadata_json_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        logger.info("Metadata guardada")

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
