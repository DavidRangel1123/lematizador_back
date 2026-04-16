# from sqlalchemy import select, func
# from sqlalchemy.ext.asyncio import AsyncSession
# from math import ceil
# from typing import Optional, List, Dict, Any

# from app.db.models.persona_desaparecida import PersonaDesaparecida


# class Queries:
#     def __init__(self, session: AsyncSession):
#         self.session = session
#         self.model = PersonaDesaparecida

#     # -----------------------------
#     # Métodos públicos
#     # -----------------------------

#     async def get_paginated_rows(self, page: int, size: int) -> Dict[str, Any]:
#         self._validate_pagination(page, size)
#         offset = (page - 1) * size

#         total_rows = await self._get_total_rows()

#         query = select(self.model).order_by(self.model.pk_row).offset(offset).limit(size)

#         result = await self.session.execute(query)
#         rows = result.scalars().all()

#         data = self._serialize(rows)

#         return {
#             "page": page,
#             "size": size,
#             "total_rows": total_rows,
#             "total_pages": ceil(total_rows / size),
#             "data": data,
#         }

#     async def get_paginated_custom_rows(
#         self,
#         page: int,
#         size: int,
#         columns: Optional[List[str]] = None,
#     ) -> Dict[str, Any]:

#         self._validate_pagination(page, size)

#         offset = (page - 1) * size

#         total_rows = await self._get_total_rows()

#         # Resolver columnas dinámicas
#         if columns:
#             selected_columns = [
#                 getattr(self.model, col) for col in columns if hasattr(self.model, col)
#             ]

#             query = select(*selected_columns)
#         else:
#             query = select(self.model)

#         query = query.order_by(self.model.pk_row).offset(offset).limit(size)

#         result = await self.session.execute(query)

#         if columns:
#             rows = result.all()
#             data = [dict(row._mapping) for row in rows]
#         else:
#             rows = result.scalars().all()
#             data = self._serialize(rows)

#         return {
#             "page": page,
#             "size": size,
#             "total_rows": total_rows,
#             "total_pages": ceil(total_rows / size),
#             "columns_returned": columns if columns else "all",
#             "data": data,
#         }

#     async def get_by_ids(self, ids: List[int]) -> List[Dict[str, Any]]:
#         """
#         Obtiene registros por una lista de pk_row (posición en BD)
        
#         Args:
#             ids: Lista de pk_row a buscar
        
#         Returns:
#             Lista de registros serializados en el orden de los IDs proporcionados
#         """
#         if not ids:
#             return []
        
#         # Eliminar duplicados y mantener el orden
#         unique_ids = list(dict.fromkeys(ids))
        
#         # Consultar los registros usando pk_row
#         query = select(self.model).where(self.model.pk_row.in_(unique_ids))
#         result = await self.session.execute(query)
#         rows = result.scalars().all()
        
#         # Crear un diccionario para acceso rápido por pk_row
#         registros_dict = {row.pk_row: row for row in rows}
        
#         # Mantener el orden original de los IDs
#         registros_ordenados = []
#         for id_ in ids:
#             if id_ in registros_dict:
#                 registro_serializado = self._serialize_single(registros_dict[id_])
#                 registros_ordenados.append(registro_serializado)
        
#         return registros_ordenados
    
#     async def get_by_vector_indices(self, vector_indices: List[int]) -> List[Dict[str, Any]]:
#         """
#         Obtiene registros por una lista de vector_index (índice del vectorizador)
        
#         Args:
#             vector_indices: Lista de vector_index a buscar (1-indexed)
        
#         Returns:
#             Lista de registros serializados en el orden de los vector_indices proporcionados
#         """
#         if not vector_indices:
#             return []
        
#         # Eliminar duplicados y mantener el orden
#         unique_indices = list(dict.fromkeys(vector_indices))
        
#         # Consultar los registros usando vector_index
#         query = select(self.model).where(self.model.vector_index.in_(unique_indices))
#         result = await self.session.execute(query)
#         rows = result.scalars().all()
        
#         # Crear un diccionario para acceso rápido por vector_index
#         registros_dict = {row.vector_index: row for row in rows}
        
#         # Mantener el orden original de los vector_indices
#         registros_ordenados = []
#         for idx in vector_indices:
#             if idx in registros_dict:
#                 registro_serializado = self._serialize_single(registros_dict[idx])
#                 registros_ordenados.append(registro_serializado)
        
#         return registros_ordenados


#     # -----------------------------
#     # Helpers internos
#     # -----------------------------
#     def _validate_pagination(self, page: int, size: int):
#         if page < 1:
#             raise ValueError("Page must be >= 1")
#         if size < 1 or size > 500:
#             raise ValueError("Size must be between 1 and 500")

#     async def _get_total_rows(self) -> int:
#         query = select(func.count()).select_from(self.model)
#         result = await self.session.execute(query)
#         return result.scalar_one()

#     def _serialize(self, rows):
#         return [
#             {k: v for k, v in row.__dict__.items() if not k.startswith("_")}
#             for row in rows
#         ]
    
#     def _serialize_single(self, row) -> Dict[str, Any]:
#         """
#         Serializa una sola fila a diccionario
#         """
#         return {
#             key: value 
#             for key, value in row.__dict__.items() 
#             if not key.startswith("_")
#         }
