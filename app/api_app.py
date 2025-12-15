"""
FastAPI App para LegalTech Suite V4.0
"""

import sys
import os

# Añadir el directorio app al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)