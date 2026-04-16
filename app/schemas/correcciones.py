from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal


# Tipo de acción permitida
TipoAccion = Literal["separacion", "stop-word", "general", "corporal", "indumentaria"]


class CorrectLema(BaseModel):
    """Schema para una corrección individual."""

    word: str = Field(..., min_length=1, description="Palabra a corregir")
    action: TipoAccion = Field(..., description="Tipo de corrección")
    correction: str = Field(..., min_length=1, description="Corrección a aplicar")

    @field_validator("word")
    @classmethod
    def validate_word(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("La palabra no puede estar vacía")
        return v.strip().lower()

    @field_validator("correction")
    @classmethod
    def validate_correction(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("La corrección no puede estar vacía")
        return v.strip().lower()


class CorreccionesList(BaseModel):
    """Schema para lista de correcciones."""

    correcciones: List[CorrectLema] = Field(
        ..., min_length=1, description="Lista de correcciones"
    )
