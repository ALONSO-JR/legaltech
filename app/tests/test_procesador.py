"""
Tests para el procesador principal
"""

import unittest
import sys
import os
import tempfile

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import RedactorLegalUltimate
import fitz

class TestRedactorLegalUltimate(unittest.TestCase):
    
    def setUp(self):
        self.procesador = RedactorLegalUltimate()
    
    def test_crear_documento_prueba(self):
        """Crea un documento de prueba para tests"""
        doc = fitz.open()
        page = doc.new_page()
        
        # Texto con datos sensibles
        texto_prueba = """
        CONTRATO DE PRUEBA
        
        Cliente: Juan Pérez
        RUT: 12.345.678-5
        Email: juan.perez@ejemplo.cl
        Teléfono: +56912345678
        Monto: $1.000.000
        
        FIRMAS:
        Juan Pérez
        """
        
        page.insert_text((50, 50), texto_prueba)
        
        # Guardar temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            doc.save(tmp.name)
            tmp_path = tmp.name
        
        doc.close()
        return tmp_path
    
    def test_deteccion_datos(self):
        """Test de detección de datos sensibles"""
        doc_path = self.test_crear_documento_prueba()
        
        try:
            # Abrir documento
            doc = fitz.open(doc_path)
            
            # Escanear documento
            lista_negra, contexto = self.procesador.escanear_documento_inteligente(doc)
            
            # Verificar que se detectaron datos
            self.assertGreater(len(lista_negra), 0, "Debería detectar al menos un dato sensible")
            
            # Verificar tipos de datos detectados
            datos_detectados = [str(d).lower() for d in lista_negra]
            
            # Verificar que se detectó el RUT
            rut_detectado = any('12.345.678-5' in str(d) or '12345678-5' in str(d) for d in lista_negra)
            self.assertTrue(rut_detectado, "Debería detectar el RUT")
            
            doc.close()
            
        finally:
            # Limpiar archivo temporal
            if os.path.exists(doc_path):
                os.remove(doc_path)
    
    def test_procesamiento_modo_revision(self):
        """Test de procesamiento en modo revisión"""
        doc_path = self.test_crear_documento_prueba()
        
        try:
            # Procesar en modo revisión
            resultado = self.procesador.procesar_pdf(
                doc_path,
                "test_revision.pdf",
                modo="revision"
            )
            
            # Verificar que se generaron resultados
            self.assertEqual(len(resultado), 4, "Debería retornar 4 valores")
            
            # Verificar que el archivo de salida existe
            self.assertTrue(os.path.exists(resultado[0]), "Archivo de salida debería existir")
            
            # Verificar que se generó reporte CSV
            self.assertTrue(os.path.exists(resultado[1]), "Reporte CSV debería existir")
            
            # Limpiar archivos generados
            for archivo in resultado[:3]:
                if os.path.exists(archivo):
                    os.remove(archivo)
                    
        finally:
            if os.path.exists(doc_path):
                os.remove(doc_path)
    
    def test_necesita_ocr(self):
        """Test de detección de necesidad de OCR"""
        # Crear documento con texto (no necesita OCR)
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Texto de prueba")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            doc.save(tmp.name)
            tmp_path = tmp.name
        
        doc.close()
        
        try:
            necesita = self.procesador.necesita_ocr(tmp_path)
            self.assertFalse(necesita, "Documento con texto no debería necesitar OCR")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    def test_es_autoridad(self):
        """Test de identificación de autoridades"""
        autoridades = [
            "Juez Juan Pérez",
            "Fiscal María González",
            "Ministro de la Corte",
            "Notario público",
            "Presidente del tribunal"
        ]
        
        no_autoridades = [
            "Juan Pérez",
            "Empresa Ejemplo S.A.",
            "Cliente particular",
            "Testigo anónimo"
        ]
        
        for autoridad in autoridades:
            self.assertTrue(self.procesador.es_autoridad(autoridad),
                          f"{autoridad} debería ser identificado como autoridad")
        
        for no_autoridad in no_autoridades:
            self.assertFalse(self.procesador.es_autoridad(no_autoridad),
                           f"{no_autoridad} NO debería ser identificado como autoridad")

if __name__ == '__main__':
    unittest.main()