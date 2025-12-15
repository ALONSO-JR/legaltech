"""
Tests para los validadores de datos
"""

import unittest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import ValidadorDatosChilenos

class TestValidadorDatosChilenos(unittest.TestCase):
    
    def setUp(self):
        self.validador = ValidadorDatosChilenos()
    
    def test_rut_valido(self):
        """Test para RUTs válidos"""
        test_cases = [
            ("12.345.678-5", True),
            ("12345678-5", True),
            ("6.789.012-3", True),
            ("12.345.678-0", False),  # DV incorrecto
            ("123", False),  # Muy corto
            ("99.999.999-9", True),  # Límite superior
        ]
        
        for rut, esperado_valido in test_cases:
            resultado = self.validador.validar_rut_completo(rut, "")
            self.assertEqual(resultado['valido'], esperado_valido, 
                           f"RUT {rut} debería ser {'válido' if esperado_valido else 'inválido'}")
    
    def test_uf_valida(self):
        """Test para valores UF"""
        test_cases = [
            ("UF 1.234,56", True),
            ("1.234,56 UF", True),
            ("UF 0.01", True),
            ("UF 100000", True),  # Valor extremo
            ("UF abc", False),  # No numérico
        ]
        
        for uf, esperado_valido in test_cases:
            resultado = self.validador.validar_contexto_uf(uf, "")
            self.assertEqual(resultado['valido'], esperado_valido,
                           f"UF {uf} debería ser {'válido' if esperado_valido else 'inválido'}")
    
    def test_email_valido(self):
        """Test para emails"""
        test_cases = [
            ("test@example.com", True),
            ("nombre.apellido@empresa.cl", True),
            ("contacto@legaltech.cl", True),
            ("test@.com", False),
            ("@dominio.com", False),
            ("sin_arroba.com", False),
        ]
        
        for email, esperado_valido in test_cases:
            resultado = self.validador.validar_email_juridico(email, "")
            self.assertEqual(resultado['valido'], esperado_valido,
                           f"Email {email} debería ser {'válido' if esperado_valido else 'inválido'}")
    
    def test_telefono_valido(self):
        """Test para teléfonos chilenos"""
        test_cases = [
            ("+56912345678", True),  # Celular con código país
            ("912345678", True),  # Celular sin código
            ("221234567", True),  # Fijo Santiago
            ("41234567", True),  # Fijo regional
            ("123456", False),  # Muy corto
            ("abcdefgh", False),  # No numérico
        ]
        
        for telefono, esperado_valido in test_cases:
            resultado = self.validador.validar_telefono_chileno(telefono, "")
            self.assertEqual(resultado['valido'], esperado_valido,
                           f"Teléfono {telefono} debería ser {'válido' if esperado_valido else 'inválido'}")
    
    def test_moneda_valida(self):
        """Test para montos monetarios"""
        test_cases = [
            ("$1.000.000", True),
            ("US$ 500", True),
            ("500 pesos", True),
            ("1.000 dólares", True),
            ("€100", True),
            ("abc", False),
        ]
        
        for moneda, esperado_valido in test_cases:
            resultado = self.validador.validar_contexto_monetario(moneda, "")
            self.assertEqual(resultado['valido'], esperado_valido,
                           f"Moneda {moneda} debería ser {'válido' if esperado_valido else 'inválido'}")

if __name__ == '__main__':
    unittest.main()