FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias del sistema (incluyendo build-essential para spaCy)
RUN apt-get update && apt-get install -y \
    curl \
    file \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root
RUN useradd -m appuser

# Copiar requirements e instalar dependencias Python
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# INSTALAR MODELO DE SPACY EN ESPAÑOL
# Esto es crítico - debe hacerse DESPUÉS de instalar spacy en requirements
RUN python -m spacy download es_core_news_md

# Crear directorio keys

# Copiar el resto del código
COPY . .

# Si tienes la carpeta con los modelos/vectorizadores guardados, asegúrate de copiarlos
COPY /app/vectores/ /app/vectores/

# Cambiar permisos del directorio
RUN chown -R appuser:appuser /app

# Cambiar a usuario no-root
USER appuser

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]