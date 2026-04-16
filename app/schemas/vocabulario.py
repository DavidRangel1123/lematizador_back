from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class VocabularioTipo(BaseModel):
    """Schema para validar el tipo de vocabulario."""

    tipo: str = Field(
        ..., description="Tipo de vocabulario: 'corporal' o 'indumentaria'"
    )

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v: str) -> str:
        tipos_validos = ["corporal", "indumentaria"]
        if v not in tipos_validos:
            raise ValueError(
                f"Tipo no válido. Debe ser 'corporal' o 'indumentaria', recibido: {v}"
            )
        return v


class VocabularioResponse(BaseModel):
    """Schema para la respuesta del vocabulario."""

    status: str = "success"
    project_id: str
    tipo: str
    total_palabras: int
    palabras: List[str]


class VocabularioCompletoResponse(BaseModel):
    """Schema para la respuesta del vocabulario completo."""

    status: str = "success"
    project_id: str
    corporal: List[str]
    indumentaria: List[str]
    total_palabras: int
    total_corporal: int
    total_indumentaria: int
