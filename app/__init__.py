"""
LegalTech Suite V4.0 - Sistema de Sanitización Documental con IA
Edición especial para el mercado legal chileno
"""

__version__ = "4.0.0"
__author__ = "LegalTech Chile"
__email__ = "contacto@legaltech.cl"
__description__ = "Sistema avanzado de privacidad y sanitización documental para el sector legal chileno"

from .main import (
    RedactorLegalUltimate,
    ValidadorDatosChilenos,
    MemoriaDocumentalContextual,
    GeneradorReportesEjecutivos,
    SistemaAprendizajeContinua,
    DashboardLegalTech,
    main,
    ejecutar_modo_directo,
    ejecutar_dashboard,
    ejecutar_api,
    ejecutar_aprendizaje,
    ejecutar_pruebas
)

__all__ = [
    'RedactorLegalUltimate',
    'ValidadorDatosChilenos',
    'MemoriaDocumentalContextual',
    'GeneradorReportesEjecutivos',
    'SistemaAprendizajeContinua',
    'DashboardLegalTech',
    'main',
    'ejecutar_modo_directo',
    'ejecutar_dashboard',
    'ejecutar_api',
    'ejecutar_aprendizaje',
    'ejecutar_pruebas'
]