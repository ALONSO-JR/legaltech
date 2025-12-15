"""
Streamlit App para LegalTech Suite V4.0
"""

import streamlit as st
import sys
import os

# Añadir el directorio app al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import DashboardLegalTech

def main():
    """
    Punto de entrada para la aplicación Streamlit
    """
    st.set_page_config(
        page_title="LegalTech Suite V4.0",
        page_icon="⚖️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Inicializar dashboard
    dashboard = DashboardLegalTech()
    
    # Configurar página
    dashboard.configurar_pagina()
    
    # Mostrar página principal
    dashboard.mostrar_pagina_principal()

if __name__ == "__main__":
    main()