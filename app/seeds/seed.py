# import asyncio
# from pathlib import Path

# from app.db.session import SessionLocal
# from app.ingestion.service import IngestionService
# from app.db.models.persona_desaparecida import PersonaDesaparecida
# from app.utils.constants import ColumnDic


# async def run_seed():
#     file_path = Path("app/data/siaba_202602191235.csv")

#     async with SessionLocal() as session:
#         service = IngestionService(session, PersonaDesaparecida, ColumnDic)
#         await service.process_file(file_path)


# if __name__ == "__main__":
#     asyncio.run(run_seed())
