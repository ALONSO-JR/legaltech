# LegalTech Suite V4.0 Dockerfile
FROM python:3.9-slim

LABEL maintainer="LegalTech Chile <contacto@legaltech.cl>"
LABEL version="4.0.0"
LABEL description="Sistema de sanitización documental con IA para el sector legal chileno"

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    ghostscript \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /app

# Crear usuario no-root
RUN useradd -m -u 1000 legaltech && \
    chown -R legaltech:legaltech /app
USER legaltech

# Variables de entorno
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV FASTAPI_PORT=8000
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata

# Copiar requirements primero para cache
COPY --chown=legaltech:legaltech app/requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    python -m spacy download es_core_news_lg

# Crear directorios necesarios
RUN mkdir -p temp resultados logs data static/images templates

# Copiar código fuente
COPY --chown=legaltech:legaltech app/ .
COPY --chown=legaltech:legaltech config.yaml .
COPY --chown=legaltech:legaltech README.md .

# Verificar instalación
RUN python -c "import spacy; nlp = spacy.load('es_core_news_lg'); print('✅ Spacy cargado correctamente')" && \
    python -c "import fitz; print('✅ PyMuPDF instalado correctamente')" && \
    python -c "import pandas as pd; print('✅ Pandas instalado correctamente')"

# Exponer puertos
EXPOSE 8501 8000

# Comando de salud
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Comando por defecto (menú interactivo)
CMD ["python", "main.py"]