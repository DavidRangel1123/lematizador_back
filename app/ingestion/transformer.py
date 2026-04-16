import pandas as pd
from .constants import DATE_COLUMNS, INT_COLUMNS, TEXT_COLUMNS
from datetime import datetime, date


class DataTransformer:
    def transform(self, df: pd.DataFrame) -> list[dict]:
        df = df.copy()

        df = self._normalize_nulls(df)

        registros = df.to_dict(orient="records")
        registros = self._parse_records(registros)

        registros = self._final_null_cleanup(registros)

        return registros

    def _normalize_nulls(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].apply(
                    lambda x: x.to_pydatetime() if pd.notnull(x) else None
                )
            else:
                df[col] = df[col].where(pd.notnull(df[col]), None)

        return df


    def _parse_records(self, registros: list[dict]) -> list[dict]:
        registros_limpios = []

        for registro in registros:
            limpio = {}

            for key, value in registro.items():

                if value is None:
                    limpio[key] = None
                    continue

                if key in TEXT_COLUMNS:
                    limpio[key] = self._parse_text(value)

                elif key in DATE_COLUMNS:
                    limpio[key] = self._parse_date(value)

                elif key in INT_COLUMNS:
                    limpio[key] = self._parse_int(value)

                else:
                    limpio[key] = value

            registros_limpios.append(limpio)

        return registros_limpios

    def _parse_text(self, value):
        if isinstance(value, float) and value.is_integer():
            return str(int(value))

        if hasattr(value, "strftime"):
            return value.strftime("%Y-%m-%d")

        return str(value).strip()

    def _parse_date(self, value):
        if isinstance(value, pd.Timestamp):
            return value.date()

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        if isinstance(value, str):
            value = value.strip()

            formats = [
                "%Y-%m-%d",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f",
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    pass

            return None

        return None

    def _parse_int(self, value):
        if isinstance(value, float):
            if value.is_integer():
                return int(value)
            return None

        if isinstance(value, str) and value.isdigit():
            return int(value)

        return None

    def _final_null_cleanup(self, records: list[dict]) -> list[dict]:
        cleaned = []

        for row in records:
            new_row = {}

            for key, value in row.items():

                # 🔥 Si por alguna razón queda un NaT
                if value is pd.NaT:
                    new_row[key] = None

                # Si es Timestamp de pandas
                elif isinstance(value, pd.Timestamp):
                    new_row[key] = value.to_pydatetime()

                else:
                    new_row[key] = value

            cleaned.append(new_row)

        return cleaned