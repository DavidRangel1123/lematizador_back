from pydantic import BaseModel, Field, field_validator
import re
from typing import List

class ColumnClassification(BaseModel):
    corporal: List[str]
    indumentaria: List[str]