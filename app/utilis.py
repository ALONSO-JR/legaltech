"""
Utilidades comunes para LegalTech Suite
"""

import os
import yaml
import logging
from typing import Dict, Any
from datetime import datetime
import hashlib
import json

def cargar_configuracion(ruta: str = "config.yaml") -> Dict[str, Any]:
    """
    Carga la configuración desde archivo YAML
    """
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"⚠️ Error cargando configuración: {e}")
        return {}

def configurar_logging(config: Dict[str, Any] = None):
    """
    Configura el sistema de logging
    """
    if config is None:
        config = cargar_configuracion()
    
    log_config = config.get('legaltech', {}).get('logging', {})
    
    nivel = getattr(logging, log_config.get('nivel', 'INFO'))
    formato = log_config.get('formato', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    archivo = log_config.get('archivo', 'legaltech.log')
    
    # Configurar logging básico
    logging.basicConfig(
        level=nivel,
        format=formato,
        handlers=[
            logging.FileHandler(archivo),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("✅ Sistema de logging configurado")
    
    return logger

def crear_directorios():
    """
    Crea los directorios necesarios para el sistema
    """
    directorios = [
        'temp',
        'resultados',
        'logs',
        'data',
        'static/images',
        'templates'
    ]
    
    for directorio in directorios:
        os.makedirs(directorio, exist_ok=True)
        print(f"📁 Directorio creado/verificado: {directorio}")

def generar_hash_archivo(ruta: str) -> str:
    """
    Genera hash SHA-256 de un archivo
    """
    sha256_hash = hashlib.sha256()
    
    try:
        with open(ruta, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"❌ Error generando hash: {e}")
        return ""

def formatear_fecha(fecha: datetime = None) -> str:
    """
    Formatea fecha para reportes
    """
    if fecha is None:
        fecha = datetime.now()
    
    return fecha.strftime("%d/%m/%Y %H:%M:%S")

def validar_extension_archivo(nombre: str, extensiones_validas: list) -> bool:
    """
    Valida la extensión de un archivo
    """
    nombre_lower = nombre.lower()
    return any(nombre_lower.endswith(ext) for ext in extensiones_validas)

def limpiar_directorio_temporal(dias_retencion: int = 7):
    """
    Limpia archivos temporales antiguos
    """
    import shutil
    import time
    
    directorio_temp = "temp"
    
    if not os.path.exists(directorio_temp):
        return
    
    tiempo_limite = time.time() - (dias_retencion * 24 * 60 * 60)
    
    for archivo in os.listdir(directorio_temp):
        ruta_archivo = os.path.join(directorio_temp, archivo)
        
        try:
            if os.path.isfile(ruta_archivo):
                if os.path.getmtime(ruta_archivo) < tiempo_limite:
                    os.remove(ruta_archivo)
                    print(f"🗑️ Archivo temporal eliminado: {archivo}")
            elif os.path.isdir(ruta_archivo):
                if os.path.getmtime(ruta_archivo) < tiempo_limite:
                    shutil.rmtree(ruta_archivo)
                    print(f"🗑️ Directorio temporal eliminado: {archivo}")
        except Exception as e:
            print(f"⚠️ Error limpiando {ruta_archivo}: {e}")

def obtener_tamano_archivo(ruta: str) -> str:
    """
    Obtiene el tamaño de un archivo en formato legible
    """
    try:
        bytes_size = os.path.getsize(ruta)
        
        for unidad in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.2f} {unidad}"
            bytes_size /= 1024.0
        
        return f"{bytes_size:.2f} TB"
    except:
        return "N/A"

def guardar_resultados_json(resultados: Dict[str, Any], ruta: str):
    """
    Guarda resultados en formato JSON
    """
    try:
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(resultados, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Error guardando JSON: {e}")
        return False

def cargar_resultados_json(ruta: str) -> Dict[str, Any]:
    """
    Carga resultados desde JSON
    """
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error cargando JSON: {e}")
        return {}