from pydantic import BaseModel, Field, field_validator
import re

class ProjectCreate(BaseModel):
    project_name: str = Field(..., min_length=1, max_length=100, description="Nombre del proyecto")
    
    @field_validator("project_name")
    @classmethod
    def validate_project_name(cls, v: str) -> str:
        # Permitir letras, números, guiones y guiones bajos
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("El nombre del proyecto solo puede contener letras, números, guiones y guiones bajos")
        return v