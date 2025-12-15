# ==============================
# LegalTech Suite V4.0 Dockerfile
# ==============================
FROM python:3.11-slim

LABEL maintainer="LegalTech Chile <contacto@legaltech.cl>"
LABEL version="4.0.1"
LABEL description="Sistema de sanitización documental con IA para el sector legal chileno"

# ==============================
# Dependencias del sistema
# ==============================
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    ghostscript \
    poppler-utils \
    build-essential \
    gcc \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# ==============================
# Directorio de trabajo
# ==============================
WORKDIR /app

# ==============================
# Usuario no-root (seguridad)
# ==============================
RUN useradd -m -u 1000 legaltech && \
    chown -R legaltech:legaltech /app
USER legaltech

# ==============================
# Variables de entorno
# ==============================
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FASTAPI_PORT=8000
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata

# ==============================
# Instalar dependencias Python
# ==============================
COPY --chown=legaltech:legaltech app/requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    python -m spacy download es_core_news_lg

# ==============================
# Crear directorios necesarios
# ==============================
RUN mkdir -p temp resultados logs data static/images templates

# ==============================
# Copiar código fuente
# ==============================
COPY --chown=legaltech:legaltech app/ .
COPY --chown=legaltech:legaltech config.yaml .
COPY --chown=legaltech:legaltech README.md .

# ==============================
# Verificación de librerías clave
# ==============================
RUN python -c "import spacy; spacy.load('es_core_news_sm'); print('✅ spaCy OK')" && \
    python -c "import fitz; print('✅ PyMuPDF OK')" && \
    python -c "import pandas as pd; print('✅ Pandas OK')"

# ==============================
# Puertos
# ==============================
EXPOSE 8000 8501

# ==============================
# Healthcheck
# ==============================
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# ==============================
# Comando de arranque
# ==============================
CMD ["uvicorn", "api_app:app", "--host", "0.0.0.0", "--port", "8000"]