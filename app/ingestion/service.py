from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeMeta
import pandas as pd

from .reader import FileReader
from .transformer import DataTransformer
from .repository import PersonaRepository


class IngestionService:
    def __init__(
        self, session: AsyncSession, model: DeclarativeMeta, column_map: dict[str, str]
    ):
        self.session = session
        self.model = model
        self.column_map = column_map
        self.reader = FileReader()
        self.transformer = DataTransformer()
        self.repository = PersonaRepository(session)

    async def process_file(self, file_path: Path) -> None:
        # EXTRACT
        df = self.reader.read(file_path)

        df = self._map_columns(df)
        df = self._filter_model_columns(df)
        df = self._valid_rows(df)
        
        # TRANSFORM
        records = self.transformer.transform(df)

        # LOAD
        async with self.session.begin():
            await self.repository.bulk_insert(records)

    def _map_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        df_internal = df.rename(columns=self.column_map)
        print("Columnas mapeadas a nombres internos")
        return df_internal

    def _filter_model_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        model_columns = {c.name for c in self.model.__table__.columns}
        columnas_comunes = df.columns.intersection(model_columns)
        # columnas_ignoradas = set(df.columns) - set(columnas_comunes)

        for col in columnas_comunes:
            print(f"Columna: '{col}'")

        print(f"📋 Columnas a insertar en BD: {len(columnas_comunes)}")

        return df[columnas_comunes]

    def _valid_rows(self, df:pd.DataFrame) -> pd.DataFrame:
        """
        Asigna vector_index solo a registros válidos, de forma consecutiva
        respetando el orden original del DataFrame
        """
        df = df.copy()
        
        # Inicializar columna vector_index con None
        df['vector_index'] = None
        
        # Contador para índices válidos (empieza en 1)
        contador = 0
        
        # Recorrer filas en orden
        for idx in range(len(df)):
            # Verificar si el registro es válido
            es_valido = (
                (pd.notna(df.loc[idx, 'tattoos_desc']) and df.loc[idx, 'tattoos_desc'] != '') or
                (pd.notna(df.loc[idx, 'sign_desc']) and df.loc[idx, 'sign_desc'] != '') or
                (pd.notna(df.loc[idx, 'clothe_desc']) and df.loc[idx, 'clothe_desc'] != '')
            )
            
            if es_valido:
                df.loc[idx, 'vector_index'] = contador
                contador += 1
        
        return df