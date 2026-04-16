import pandas as pd
from pathlib import Path


class FileReader:
    def read(self, file_path: Path) -> pd.DataFrame:
        if file_path.suffix == ".xlsx":
            return pd.read_excel(file_path)

        if file_path.suffix == ".csv":
            return pd.read_csv(file_path)

        raise ValueError("Formato de archivo no soportado")
