# from sqlalchemy.ext.asyncio import AsyncSession
# from app.db.models.persona_desaparecida import PersonaDesaparecida


# class PersonaRepository:
#     def __init__(self, session: AsyncSession):
#         self.session = session

#     async def bulk_insert(self, records: list[dict]) -> None:
#         objects = [PersonaDesaparecida(**record) for record in records]

#         self.session.add_all(objects)
