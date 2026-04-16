from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.db.database import Base


class Proyecto(Base):
    __tablename__ = "proyecto"

    # ===================================================
    # Identificadores
    # ===================================================
    pk_row = Column(Integer, primary_key=True)  # PK
    
    # ===================================================
    # Nombre
    # ===================================================
    nombre = Column(String(200), nullable=False)
    
    # ===================================================
    # Metadata
    # ===================================================
    created_at = Column(DateTime, server_default=func.now(), nullable=True)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=True
    )