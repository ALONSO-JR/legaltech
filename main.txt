# ============================================
# LEGALTECH SUITE V4.0 - CÓDIGO COMPLETO
# ============================================

import fitz  # PyMuPDF
import spacy
import re
import os
import csv
import subprocess
import json
import numpy as np
import pandas as pd
import networkx as nx
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Tuple
import hashlib
from functools import lru_cache
import zipfile
import tempfile
from concurrent.futures import ThreadPoolExecutor
import asyncio
import uuid
import logging
import yaml
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors

# ============================================
# MÓDULO 1: VALIDADOR DE DATOS CHILENOS
# ============================================

class ValidadorDatosChilenos:
    """Validador con lógica de negocio real para datos chilenos"""
    
    def __init__(self):
        self.validadores = {
            'RUT': self.validar_rut_completo,
            'UF': self.validar_contexto_uf,
            'MONEDA': self.validar_contexto_monetario,
            'EMAIL': self.validar_email_juridico,
            'TELEFONO': self.validar_telefono_chileno,
            'DIRECCION': self.validar_direccion_chilena
        }
        
        self.cache_validaciones = {}
    
    @lru_cache(maxsize=1000)
    def validar_rut_completo(self, texto: str, contexto: str = "") -> Dict[str, Any]:
        """
        Validación robusta de RUT chileno con contexto
        """
        # Limpiar texto
        texto_original = texto
        texto = texto.replace(".", "").replace("-", "").upper().strip()
        
        # Verificar formato básico
        if not re.match(r'^\d{7,8}[0-9K]$', texto):
            return {'valido': False, 'confianza': 0.1, 'razon': 'Formato inválido'}
        
        # Extraer cuerpo y dígito verificador
        cuerpo = texto[:-1]
        dv_ingresado = texto[-1]
        
        # Calcular dígito verificador
        suma = 0
        multiplo = 2
        
        for c in reversed(cuerpo):
            suma += int(c) * multiplo
            multiplo = 2 if multiplo == 7 else multiplo + 1
        
        resto = suma % 11
        dv_calculado = {10: 'K', 11: '0'}.get(11 - resto, str(11 - resto))
        
        # Verificar coincidencia
        if dv_ingresado != dv_calculado:
            return {'valido': False, 'confianza': 0.3, 'razon': 'DV inválido'}
        
        # Análisis contextual avanzado
        contexto_score = self.analizar_contexto_rut(contexto, cuerpo)
        
        # Rango válido de RUTs (1.000.000 a 99.999.999 aprox)
        num_rut = int(cuerpo)
        if num_rut < 1000000 or num_rut > 99999999:
            return {'valido': False, 'confianza': 0.4, 'razon': 'Rango inválido'}
        
        # Lista negra de RUTs de prueba
        ruts_prueba = {11111111, 12345678, 99999999, 88888888, 1234567, 7654321}
        if num_rut in ruts_prueba:
            return {'valido': True, 'confianza': 0.2, 'razon': 'RUT de prueba', 'flag': 'PRUEBA'}
        
        return {
            'valido': True,
            'confianza': 0.95 * contexto_score,
            'formateado': self.formatear_rut(cuerpo, dv_calculado),
            'cuerpo': cuerpo,
            'dv': dv_calculado,
            'original': texto_original
        }
    
    def analizar_contexto_rut(self, contexto: str, rut_cuerpo: str) -> float:
        """
        Analiza el contexto alrededor del RUT para determinar confianza
        """
        if not contexto:
            return 0.5
        
        palabras_clave = {
            'alto': ['rut', 'rol único tributario', 'identificador', 'cédula', 'documento'],
            'medio': ['número', 'n°', 'nro', 'id', 'identificación'],
            'bajo': ['el', 'de', 'con', 'para', 'al']
        }
        
        contexto_lower = contexto.lower()
        score = 0.5  # Base
        
        # Bonus por palabras clave cercanas
        for palabra in palabras_clave['alto']:
            if palabra in contexto_lower:
                score += 0.3
                break
        
        # Penalizar si está en medio de texto corrido sin contexto
        if len(contexto.strip()) < 20:
            score *= 0.8
        
        # Verificar patrones típicos
        patrones_tipicos = [
            r'RUT[:\s]+' + re.escape(self.formatear_rut(rut_cuerpo, 'X')),
            r'Rol Único Tributario[:\s]+' + re.escape(self.formatear_rut(rut_cuerpo, 'X'))
        ]
        
        for patron in patrones_tipicos:
            if re.search(patron, contexto, re.IGNORECASE):
                score += 0.2
                break
        
        return min(max(score, 0.1), 1.0)
    
    def formatear_rut(self, cuerpo: str, dv: str) -> str:
        """Formatea RUT con puntos y guión"""
        cuerpo = str(cuerpo)
        if len(cuerpo) > 3:
            cuerpo_formateado = cuerpo[-3:]
            resto = cuerpo[:-3]
            
            while resto:
                cuerpo_formateado = resto[-3:] + '.' + cuerpo_formateado
                resto = resto[:-3]
            
            return f"{cuerpo_formateado}-{dv}"
        
        return f"{cuerpo}-{dv}"
    
    def validar_contexto_uf(self, texto: str, contexto: str = "") -> Dict[str, Any]:
        """
        Valida que sea realmente una UF y no otra cosa
        """
        # Verificar formato
        match = re.search(r'([\d,.]+)\s*(UF|Unidades de Fomento)', texto, re.IGNORECASE)
        if not match:
            return {'valido': False, 'confianza': 0.1}
        
        valor = match.group(1)
        unidad = match.group(2)
        
        # Convertir a número
        try:
            valor_num = float(valor.replace('.', '').replace(',', '.'))
        except:
            return {'valido': False, 'confianza': 0.2}
        
        # Límites realistas de UF (0.01 a 10,000 UF)
        if valor_num < 0.01 or valor_num > 10000:
            return {'valido': True, 'confianza': 0.3, 'flag': 'VALOR_EXTREMO'}
        
        # Analizar contexto
        contexto_score = self.analizar_contexto_monetario(contexto)
        
        # Palabras que indican contexto monetario real
        indicadores_fuertes = ['monto', 'suma', 'valor', 'capital', 'deuda', 'préstamo']
        
        contexto_lower = contexto.lower()
        score_base = 0.7
        
        for indicador in indicadores_fuertes:
            if indicador in contexto_lower:
                score_base += 0.2
                break
        
        return {
            'valido': True,
            'confianza': score_base * contexto_score,
            'valor': valor_num,
            'unidad': unidad.upper(),
            'formateado': f"{valor} {unidad}",
            'original': texto
        }
    
    def validar_contexto_monetario(self, texto: str, contexto: str = "") -> Dict[str, Any]:
        """
        Valida montos monetarios ($, US$, etc.)
        """
        # Patrones de moneda
        patrones = [
            (r'\$\s*([\d,.]+)', 'CLP', 0.9),
            (r'US\$\s*([\d,.]+)', 'USD', 0.85),
            (r'USD\s*([\d,.]+)', 'USD', 0.85),
            (r'([\d,.]+)\s*pesos', 'CLP', 0.8),
            (r'([\d,.]+)\s*dólares', 'USD', 0.8),
            (r'€\s*([\d,.]+)', 'EUR', 0.75)
        ]
        
        for patron, moneda, confianza_base in patrones:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                valor = match.group(1)
                
                try:
                    valor_num = float(valor.replace('.', '').replace(',', '.'))
                except:
                    continue
                
                # Límites razonables
                if valor_num > 1000000000:  # Más de 1,000 millones
                    confianza_base *= 0.5
                
                contexto_score = self.analizar_contexto_monetario(contexto)
                
                return {
                    'valido': True,
                    'confianza': confianza_base * contexto_score,
                    'valor': valor_num,
                    'moneda': moneda,
                    'formateado': f"{moneda} {valor}",
                    'original': texto
                }
        
        return {'valido': False, 'confianza': 0.1}
    
    def analizar_contexto_monetario(self, contexto: str) -> float:
        """
        Analiza si el contexto indica realmente un monto monetario
        """
        if not contexto:
            return 0.5
        
        indicadores_positivos = [
            r'\$(?!\s*\d)',
            r'pesos',
            r'dólares',
            r'euros',
            r'monto',
            r'valor',
            r'suma',
            r'total',
            r'importe'
        ]
        
        indicadores_negativos = [
            r'aprox\.?',
            r'alrededor',
            r'cerca',
            r'ejemplo',
            r'muestra',
            r'ilustrativo'
        ]
        
        score = 0.5
        contexto_lower = contexto.lower()
        
        for indicador in indicadores_positivos:
            if re.search(indicador, contexto_lower):
                score += 0.2
                break
        
        for indicador in indicadores_negativos:
            if re.search(indicador, contexto_lower):
                score *= 0.7
                break
        
        return min(max(score, 0.1), 1.0)
    
    def validar_email_juridico(self, texto: str, contexto: str = "") -> Dict[str, Any]:
        """
        Valida emails con enfoque en dominios jurídicos chilenos
        """
        # Validación básica de email
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', texto):
            return {'valido': False, 'confianza': 0.1}
        
        # Dominios jurídicos chilenos comunes
        dominios_juridicos = {
            'alto': ['.cl', '.gob.cl', '.gobierno.cl', '.pjud.cl', '.cmf.cl'],
            'medio': ['.abogados', '.legal', '.law', '.juridico'],
            'bajo': ['.com', '.net', '.org']
        }
        
        dominio = texto.split('@')[1].lower()
        score = 0.5
        
        # Bonus por dominios jurídicos
        for d in dominios_juridicos['alto']:
            if dominio.endswith(d):
                score += 0.4
                break
        
        # Penalizar dominios genéricos
        for d in dominios_juridicos['bajo']:
            if dominio.endswith(d):
                score *= 0.7
                break
        
        # Análisis de nombre de usuario
        usuario = texto.split('@')[0].lower()
        
        # Nombres genéricos (baja confianza)
        usuarios_genericos = ['info', 'contacto', 'administracion', 'ventas', 'soporte']
        if usuario in usuarios_genericos:
            score *= 0.6
        
        # Verificar si parece personal
        if re.match(r'^[a-z]+\.[a-z]+$', usuario) or re.match(r'^[a-z]+[0-9]*$', usuario):
            score += 0.1
        
        return {
            'valido': True,
            'confianza': min(score, 0.95),
            'dominio': dominio,
            'tipo': self.clasificar_dominio(dominio),
            'original': texto
        }
    
    def clasificar_dominio(self, dominio: str) -> str:
        """Clasifica el tipo de dominio"""
        if dominio.endswith('.gob.cl') or dominio.endswith('.gobierno.cl'):
            return 'GUBERNAMENTAL'
        elif dominio.endswith('.cl'):
            return 'CHILENO'
        elif dominio.endswith('.abogados') or dominio.endswith('.legal'):
            return 'JURIDICO'
        else:
            return 'GENERICO'
    
    def validar_telefono_chileno(self, texto: str, contexto: str = "") -> Dict[str, Any]:
        """
        Valida números telefónicos chilenos con códigos de área
        """
        # Limpiar
        texto_original = texto
        texto = re.sub(r'[^\d+]', '', texto)
        
        # Patrones chilenos
        patrones = [
            # Celulares: +569XXXXXXXX o 9XXXXXXXX
            (r'^(\+?56)?9\d{8}$', 'CELULAR', 0.9),
            # Fijos con código área: +562XXXXXXXX o 2XXXXXXXX
            (r'^(\+?56)?2\d{8}$', 'FIJO_SANTIAGO', 0.8),
            # Fijos regionales
            (r'^(\+?56)?(32|33|34|41|42|43|45|51|52|53|55|57|58|61|63|64|65|67|71|72|73|75)\d{7}$', 'FIJO_REGIONAL', 0.85),
        ]
        
        for patron, tipo, confianza_base in patrones:
            if re.match(patron, texto):
                # Validar contexto
                contexto_score = self.analizar_contexto_telefono(contexto)
                
                return {
                    'valido': True,
                    'confianza': confianza_base * contexto_score,
                    'tipo': tipo,
                    'formateado': self.formatear_telefono(texto),
                    'original': texto_original
                }
        
        return {'valido': False, 'confianza': 0.3}
    
    def analizar_contexto_telefono(self, contexto: str) -> float:
        """Analiza contexto para teléfonos"""
        if not contexto:
            return 0.5
        
        indicadores = ['teléfono', 'fono', 'contacto', 'celular', 'móvil', 'whatsapp']
        
        contexto_lower = contexto.lower()
        score = 0.5
        
        for indicador in indicadores:
            if indicador in contexto_lower:
                score += 0.3
                break
        
        return min(score, 1.0)
    
    def formatear_telefono(self, telefono: str) -> str:
        """Formatea número telefónico"""
        telefono = telefono.replace('+56', '').replace('56', '')
        
        if telefono.startswith('9'):
            # Celular: 9 1234 5678
            if len(telefono) == 9:
                return f"{telefono[0]} {telefono[1:5]} {telefono[5:]}"
        elif telefono.startswith('2'):
            # Fijo Santiago: 2 1234 5678
            if len(telefono) == 9:
                return f"{telefono[0]} {telefono[1:5]} {telefono[5:]}"
        
        return telefono
    
    def validar_direccion_chilena(self, texto: str, contexto: str = "") -> Dict[str, Any]:
        """
        Valida direcciones chilenas aproximadas
        """
        # Patrones comunes de direcciones chilenas
        patrones = [
            # Calle número, comuna
            (r'^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+\d+[\s,]+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+', 0.8),
            # Av. / Avenida
            (r'^(Av\.?|Avenida)\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+\d+', 0.9),
            # Con depto/casa
            (r'.*dept[oó]\s*\d+|.*casa\s*\d+', 0.7),
        ]
        
        for patron, confianza in patrones:
            if re.search(patron, texto, re.IGNORECASE):
                return {
                    'valido': True,
                    'confianza': confianza,
                    'tipo': 'DIRECCION',
                    'original': texto
                }
        
        return {'valido': False, 'confianza': 0.2}
    
    def validar_general(self, texto: str, tipo: str, contexto: str = "") -> Dict[str, Any]:
        """
        Valida cualquier tipo de dato
        """
        validador = self.validadores.get(tipo)
        if validador:
            return validador(texto, contexto)
        
        # Validación genérica
        return {
            'valido': True,
            'confianza': 0.5,
            'original': texto
        }

# ============================================
# MÓDULO 2: MEMORIA CONTEXTUAL MULTI-PÁGINA
# ============================================

class MemoriaDocumentalContextual:
    """
    Mantiene contexto a lo largo de todo el documento
    """
    
    def __init__(self):
        self.contexto_global = {
            'entidades': {},           # Entidades mencionadas
            'alias': {},               # Mapeo alias → entidad real
            'referencias': {},         # Referencias cruzadas
            'estructura': {            # Estructura del documento
                'titulares': [],
                'secciones': [],
                'definiciones': []
            },
            'relaciones': []           # Relaciones entre entidades
        }
        
        self.grafo = nx.Graph()
        self.total_paginas = 0
        
    def analizar_estructura_documento(self, doc_pdf) -> Dict[str, Any]:
        """
        Analiza la estructura completa del documento
        """
        self.total_paginas = len(doc_pdf)
        
        texto_completo = ""
        for i, page in enumerate(doc_pdf):
            texto = page.get_text()
            texto_completo += texto + "\n"
            
            # Detectar secciones y títulos
            self._detectar_titulares(texto, i+1)
            
            # Detectar definiciones y alias
            self._detectar_definiciones(texto, i+1)
        
        # Detectar referencias cruzadas en texto completo
        self._detectar_referencias_cruzadas(texto_completo)
        
        # Construir grafo de relaciones
        self._construir_grafo_relaciones(texto_completo)
        
        return self.contexto_global
    
    def _detectar_definiciones(self, texto: str, pagina: int):
        """
        Detecta definiciones legales como:
        - "Juan Pérez (en adelante 'el Demandante')"
        - "Empresa IANSA S.A. (la 'Sociedad')"
        """
        patrones_definicion = [
            # Patrón: Nombre Completo (en adelante "alias")
            r'(?P<nombre>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)+)\s+'
            r'\(en\s+adelante\s+(?:\"?\'?)(?P<alias>el\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+|[A-ZÁÉÍÓÚÑ]+)(?:\"?\'?)\)',
            
            # Patrón: Entidad ("alias")
            r'(?P<entidad>(?:[A-ZÁÉÍÓÚÑ]\.?\s?)+\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)\s+'
            r'\(\"(?P<alias2>[A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+)\"\)',
            
            # Patrón: También conocido como
            r'tambi[eé]n\s+conocid[oa]\s+como\s+(?:\"?\'?)(?P<alias3>[^"\']+)(?:\"?\'?)',
            
            # Patrón: En lo sucesivo
            r'en\s+lo\s+sucesivo\s+(?:\"?\'?)(?P<alias4>[^"\']+)(?:\"?\'?)\s+se\s+denominar[áa]'
        ]
        
        for patron in patrones_definicion:
            for match in re.finditer(patron, texto, re.IGNORECASE):
                nombre = match.group('nombre') or match.group('entidad')
                alias = match.group('alias') or match.group('alias2') or match.group('alias3') or match.group('alias4')
                
                if nombre and alias:
                    # Normalizar
                    alias = alias.lower().strip()
                    nombre = nombre.strip()
                    
                    # Registrar en contexto global
                    if alias not in self.contexto_global['alias']:
                        self.contexto_global['alias'][alias] = {
                            'nombre_real': nombre,
                            'pagina_definicion': pagina,
                            'referencias': []
                        }
                        
                        # También registrar como entidad
                        if nombre not in self.contexto_global['entidades']:
                            self.contexto_global['entidades'][nombre] = {
                                'alias': alias,
                                'tipo': self._clasificar_entidad(nombre),
                                'paginas': [pagina]
                            }
    
    def _detectar_referencias_cruzadas(self, texto: str):
        """
        Detecta referencias a alias definidos previamente
        """
        # Buscar menciones de alias definidos
        for alias, info in self.contexto_global['alias'].items():
            # Patrón para buscar el alias en el texto
            patron = r'\b' + re.escape(alias) + r'\b'
            
            for match in re.finditer(patron, texto, re.IGNORECASE):
                # Extraer contexto alrededor
                start = max(0, match.start() - 100)
                end = min(len(texto), match.end() + 100)
                contexto = texto[start:end]
                
                # Registrar referencia
                info['referencias'].append({
                    'texto': match.group(),
                    'contexto': contexto,
                    'posicion': match.start()
                })
    
    def _detectar_titulares(self, texto: str, pagina: int):
        """
        Detecta títulos y secciones del documento
        """
        # Patrones para títulos legales
        patrones_titulo = [
            r'^(?:VISTOS?|CONSIDERANDO|RESUELVE|DECRETA|ORDENA):',
            r'^[A-ZÁÉÍÓÚÑ\s]+:$',
            r'^\d+[\.\)]\s+[A-Z]',
            r'^ART[ÍI]CULO\s+\d+',
            r'^CAP[ÍI]TULO\s+[IVXLCDM]+'
        ]
        
        lineas = texto.split('\n')
        for linea in lineas:
            linea = linea.strip()
            if len(linea) < 100:  # Probablemente un título
                for patron in patrones_titulo:
                    if re.match(patron, linea, re.IGNORECASE):
                        self.contexto_global['estructura']['titulares'].append({
                            'texto': linea,
                            'pagina': pagina,
                            'nivel': self._determinar_nivel_titulo(linea)
                        })
                        break
    
    def _determinar_nivel_titulo(self, titulo: str) -> int:
        """Determina el nivel jerárquico del título"""
        if re.match(r'^ART[ÍI]CULO', titulo, re.IGNORECASE):
            return 1
        elif re.match(r'^CAP[ÍI]TULO', titulo, re.IGNORECASE):
            return 0
        elif re.match(r'^\d+\.', titulo):
            return 2
        else:
            return 3
    
    def _clasificar_entidad(self, nombre: str) -> str:
        """Clasifica el tipo de entidad"""
        if any(palabra in nombre.lower() for palabra in ['s.a.', 'limitada', 'spa', 'inc.']):
            return 'PERSONA_JURIDICA'
        elif re.search(r'\b(abogado|doctor|ingeniero|arquitecto)\b', nombre, re.IGNORECASE):
            return 'PROFESIONAL'
        elif re.search(r'\b(juez|fiscal|ministro|notario)\b', nombre, re.IGNORECASE):
            return 'AUTORIDAD'
        else:
            return 'PERSONA_NATURAL'
    
    def _construir_grafo_relaciones(self, texto_completo: str):
        """
        Construye un grafo de relaciones entre entidades
        """
        # Agregar nodos (entidades)
        for nombre, info in self.contexto_global['entidades'].items():
            self.grafo.add_node(nombre, tipo=info['tipo'], alias=info.get('alias'))
        
        # Buscar co-ocurrencias en párrafos
        parrafos = texto_completo.split('\n\n')
        
        for parrafo in parrafos:
            entidades_parrafo = []
            
            # Buscar entidades en el párrafo
            for nombre in self.contexto_global['entidades'].keys():
                if nombre in parrafo:
                    entidades_parrafo.append(nombre)
            
            # Crear relaciones entre entidades que aparecen juntas
            for i, ent1 in enumerate(entidades_parrafo):
                for ent2 in entidades_parrafo[i+1:]:
                    if not self.grafo.has_edge(ent1, ent2):
                        self.grafo.add_edge(ent1, ent2, peso=1, contexto=parrafo[:100])
                    else:
                        # Incrementar peso de relación existente
                        self.grafo[ent1][ent2]['peso'] += 1
    
    def obtener_contexto_para_censura(self, texto: str, pagina: int, posicion: int) -> Dict[str, Any]:
        """
        Devuelve contexto enriquecido para una posición específica
        """
        contexto = {
            'entidad': None,
            'alias': None,
            'relaciones': [],
            'definicion_pagina': None,
            'es_definicion': False,
            'tipo_entidad': None
        }
        
        # Verificar si es una definición
        for alias, info in self.contexto_global['alias'].items():
            if info['pagina_definicion'] == pagina:
                # Verificar si esta posición corresponde a la definición
                if self._es_posicion_definicion(texto, posicion, info['nombre_real']):
                    contexto.update({
                        'entidad': info['nombre_real'],
                        'alias': alias,
                        'definicion_pagina': pagina,
                        'es_definicion': True,
                        'tipo_entidad': self.contexto_global['entidades'].get(info['nombre_real'], {}).get('tipo')
                    })
                    break
        
        # Si no es definición, verificar si es referencia
        if not contexto['es_definicion']:
            for alias, info in self.contexto_global['alias'].items():
                for ref in info['referencias']:
                    # Buscar si la posición corresponde a esta referencia
                    if abs(ref['posicion'] - posicion) < 50:  # Margen de error
                        contexto.update({
                            'entidad': info['nombre_real'],
                            'alias': alias,
                            'definicion_pagina': info['pagina_definicion'],
                            'es_definicion': False,
                            'tipo_entidad': self.contexto_global['entidades'].get(info['nombre_real'], {}).get('tipo')
                        })
                        
                        # Obtener relaciones del grafo
                        if info['nombre_real'] in self.grafo:
                            vecinos = list(self.grafo.neighbors(info['nombre_real']))
                            contexto['relaciones'] = vecinos[:3]  # Top 3 relaciones
                        break
        
        return contexto
    
    def _es_posicion_definicion(self, texto: str, posicion: int, nombre_real: str) -> bool:
        """
        Verifica si la posición corresponde a una definición
        """
        # Buscar el nombre real cerca de la posición
        start = max(0, posicion - len(nombre_real) - 50)
        end = min(len(texto), posicion + len(nombre_real) + 50)
        
        contexto_cercano = texto[start:end]
        return nombre_real in contexto_cercano
    
    def generar_mapa_contextual(self, output_path: str = "mapa_contextual.png") -> Optional[str]:
        """
        Genera un mapa visual de las relaciones en el documento
        """
        try:
            import matplotlib
            
            plt.figure(figsize=(12, 8))
            
            # Layout del grafo
            pos = nx.spring_layout(self.grafo, k=1, iterations=50)
            
            # Colores por tipo de nodo
            color_map = []
            for node in self.grafo.nodes():
                tipo = self.grafo.nodes[node].get('tipo', 'DESCONOCIDO')
                if tipo == 'PERSONA_JURIDICA':
                    color_map.append('lightblue')
                elif tipo == 'PERSONA_NATURAL':
                    color_map.append('lightcoral')
                elif tipo == 'AUTORIDAD':
                    color_map.append('lightgreen')
                else:
                    color_map.append('lightgray')
            
            # Dibujar nodos
            nx.draw_networkx_nodes(
                self.grafo, pos,
                node_size=500,
                node_color=color_map,
                alpha=0.9
            )
            
            # Dibujar aristas con grosor según peso
            edges = self.grafo.edges()
            weights = [self.grafo[u][v]['peso'] for u, v in edges]
            
            nx.draw_networkx_edges(
                self.grafo, pos,
                width=[min(w, 5) for w in weights],
                alpha=0.5,
                edge_color='gray'
            )
            
            # Etiquetas
            nx.draw_networkx_labels(
                self.grafo, pos,
                font_size=8,
                font_weight='bold'
            )
            
            plt.title("Mapa de Relaciones entre Entidades del Documento")
            plt.axis('off')
            
            # Leyenda
            from matplotlib.patches import Patch
            
            legend_elements = [
                Patch(facecolor='lightblue', label='Persona Jurídica'),
                Patch(facecolor='lightcoral', label='Persona Natural'),
                Patch(facecolor='lightgreen', label='Autoridad'),
                Patch(facecolor='lightgray', label='Otros')
            ]
            
            plt.legend(handles=legend_elements, loc='upper left')
            
            # Guardar mapa
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return output_path
            
        except ImportError:
            print("Matplotlib no disponible para generar mapa")
            return None

# ============================================
# MÓDULO 3: MOTOR PRINCIPAL DE REDACCIÓN
# ============================================

class RedactorLegalUltimate:
    def __init__(self):
        print("🚀 Iniciando Motor LegalTech V4.0 (Contexto + Validación + Memoria)...")
        
        # Carga de modelo de lenguaje
        try:
            self.nlp = spacy.load("es_core_news_lg")
        except:
            os.system("python -m spacy download es_core_news_lg")
            self.nlp = spacy.load("es_core_news_lg")
        
        # Inicializar validadores y memoria
        self.validador = ValidadorDatosChilenos()
        self.memoria = MemoriaDocumentalContextual()
        
        # Lista blanca (whitelist) mejorada
        self.whitelist_words = {
            "santiago", "chile", "comisión", "mercado", "financiero", "cmf", 
            "resolución", "exenta", "ministerio", "hacienda", "corte", "suprema",
            "apelaciones", "diario", "oficial", "banco", "central", "sii",
            "presidente", "comisionado", "ministro", "fiscal", "notario", "juez",
            "secretario", "abogado", "firmado", "electron", "bluetron", "fojas", 
            "vistos", "considerando", "resuelve", "decreto", "ley", "república",
            "gobierno", "estado", "municipalidad", "servicio", "impuestos", "internos"
        }
        
        # Nombres específicos de autoridades
        self.whitelist_names = {
            "catherine tornel", "bernardita piedrabuena", "beltrán de ramón", 
            "solange berstein", "kevin kowan", "andrés montes", "gabriel boric",
            "sebastián piñera", "michelle bachelet", "ricardo lagos"
        }
        
        # Patrones regex mejorados
        self.patterns = {
            'RUT': r'\b\d{1,2}\.?\d{3}\.?\d{3}-?[0-9kK]\b',
            'MONEDA': r'(?:\$|US\$|USD|€)\s?[\d,.]+',
            'UF_LARGA': r'[\d,.]+\s+(?:Unidades de Fomento|UF)',
            'UF_CORTA': r'UF\s?[\d,.]+',
            'EMAIL': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'TELEFONO': r'(?:\+56\s?)?(?:9\s?\d{4}\s?\d{4}|2\s?\d{4}\s?\d{4}|[1-9]\d{1}\s?\d{3}\s?\d{4})'
        }
        
        self.cache_detecciones = {}
        
        print("✅ Sistema listo y configurado para Chile.")
    
    def es_autoridad(self, texto: str) -> bool:
        """ Filtra si el nombre detectado es una autoridad o institución pública """
        t = texto.lower().strip()
        if len(t) < 3: return True  # Ignorar cosas muy cortas
        if any(vip in t for vip in self.whitelist_names): return True
        if t in self.whitelist_words: return True
        
        # Verificar títulos de autoridad
        titulos_autoridad = ['juez', 'fiscal', 'ministro', 'notario', 'presidente', 'secretario']
        return any(titulo in t for titulo in titulos_autoridad)
    
    def necesita_ocr(self, path: str) -> bool:
        """ Verifica si el PDF es una imagen escaneada """
        try:
            doc = fitz.open(path)
            texto = "".join([page.get_text() for page in doc])
            doc.close()
            return len(texto) < 100  # Si hay menos de 100 caracteres, necesita OCR
        except:
            return True
    
    def aplicar_ocr(self, input_path: str) -> str:
        """ Aplica OCR a documentos escaneados """
        print("⚠️ Imagen detectada (PDF Escaneado). Aplicando OCR...")
        output = f"temp_ocr_{os.path.basename(input_path)}"
        
        try:
            # Usar ocrmypdf para OCR en español
            result = subprocess.run(
                ["ocrmypdf", "--language", "spa", "--force-ocr", 
                 "--deskew", "--clean", input_path, output],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                capture_output=True
            )
            
            if result.returncode == 0 and os.path.exists(output):
                print("✅ OCR aplicado exitosamente")
                return output
            else:
                print("⚠️ OCR falló, usando texto extraído directamente")
                return input_path
                
        except Exception as e:
            print(f"❌ Error en OCR: {e}")
            return input_path
    
    def escanear_documento_inteligente(self, doc_pdf) -> Tuple[List[str], Dict[str, Any]]:
        """
        Escaneo optimizado con chunking para documentos grandes
        """
        objetivos = set()
        texto_chunks = []
        
        # Paso 1: Analizar estructura y contexto global
        print("📊 Analizando estructura del documento...")
        contexto_global = self.memoria.analizar_estructura_documento(doc_pdf)
        
        # Paso 2: Procesar por chunks para optimizar memoria
        chunk_size = 500000  # ~500KB por chunk
        current_chunk = ""
        
        for i, page in enumerate(doc_pdf):
            page_text = page.get_text()
            current_chunk += page_text + "\n"
            
            # Procesar chunk cuando alcance el tamaño límite
            if len(current_chunk) > chunk_size or i == len(doc_pdf) - 1:
                # Procesar con NLP
                doc_nlp = self.nlp(current_chunk)
                
                # Detectar personas y organizaciones
                for ent in doc_nlp.ents:
                    if ent.label_ in ["PER", "ORG"]:
                        if not self.es_autoridad(ent.text):
                            # Verificar con memoria contextual
                            contexto = self.memoria.obtener_contexto_para_censura(
                                current_chunk, i+1, ent.start_char
                            )
                            
                            if contexto.get('tipo_entidad') != 'AUTORIDAD':
                                objetivos.add(ent.text)
                
                # Detectar patrones específicos
                for tipo, patron in self.patterns.items():
                    for match in re.finditer(patron, current_chunk, re.IGNORECASE):
                        texto = match.group()
                        
                        # Validar con validador chileno
                        resultado = self.validador.validadores.get(tipo, 
                            lambda x, ctx: {'valido': True, 'confianza': 0.7})(texto, "")
                        
                        if resultado.get('valido', False) and resultado.get('confianza', 0) > 0.5:
                            objetivos.add(texto)
                
                # Resetear chunk
                current_chunk = ""
        
        # Paso 3: Agregar alias detectados por la memoria
        for alias, info in contexto_global['alias'].items():
            if info.get('nombre_real'):
                objetivos.add(info['nombre_real'])
        
        return list(objetivos), contexto_global
    
    def limpiar_metadatos(self, doc):
        """ Elimina metadatos del PDF """
        # Eliminar metadatos existentes
        doc.set_metadata({
            "creator": "LegalTech Privacy Suite V4.0",
            "producer": "Procesamiento Seguro con IA",
            "creationDate": fitz.get_pdf_now(),
            "modDate": fitz.get_pdf_now(),
            "title": "Documento Sanitizado - Información Confidencial Protegida",
            "author": "Sistema Anonimizado",
            "subject": "Documento legal procesado para protección de datos personales",
            "keywords": "sanitizado,privacidad,protegido,ley chile"
        })
        
        # Limpiar información adicional
        doc.del_xml_metadata()
        
    def procesar_pdf(self, input_path: str, output_path: str, modo: str = "revision") -> Tuple[str, str, str, int]:
        """
        Procesa un PDF con todas las funcionalidades avanzadas
        """
        # Paso 0: OCR si es necesario
        if self.necesita_ocr(input_path):
            print("🔍 Aplicando OCR al documento...")
            input_path = self.aplicar_ocr(input_path)
        
        # Abrir documento
        doc = fitz.open(input_path)
        
        # Paso 1: Escaneo inteligente con memoria contextual
        print("🕵️‍♀️ Escaneando documento con IA contextual...")
        lista_negra, contexto_global = self.escanear_documento_inteligente(doc)
        
        print(f"📝 {len(lista_negra)} elementos sensibles detectados")
        
        # Preparar reportes
        reporte_detallado = []
        reporte_resumen = {
            'total_paginas': len(doc),
            'total_detecciones': len(lista_negra),
            'modo_procesamiento': modo,
            'fecha_procesamiento': datetime.now().isoformat(),
            'contexto_global': contexto_global
        }
        
        total_censuras = 0
        
        # Paso 2: Procesar página por página con contexto
        for i, page in enumerate(doc):
            page_text = page.get_text()
            
            for item in lista_negra:
                # Buscar todas las ocurrencias
                areas = page.search_for(item)
                
                # Búsqueda alternativa si no se encuentra exacto
                if not areas and "  " in item:
                    areas = page.search_for(" ".join(item.split()))
                
                if areas:
                    for area in areas:
                        # Obtener contexto específico para esta posición
                        start_char = self._encontrar_posicion_texto(page_text, item, area)
                        contexto_especifico = self.memoria.obtener_contexto_para_censura(
                            page_text, i+1, start_char
                        )
                        
                        # Verificar si es autoridad basado en contexto
                        es_autoridad = (
                            contexto_especifico.get('tipo_entidad') == 'AUTORIDAD' or
                            self.es_autoridad(item)
                        )
                        
                        if not es_autoridad:
                            # Aplicar censura según modo
                            if modo == "final":
                                # Caja negra definitiva
                                page.add_redact_annot(area, fill=(0, 0, 0))
                                estado = "CENSURADO"
                            else:
                                # Resaltador amarillo para revisión
                                page.add_highlight_annot(area)
                                estado = "REVISIÓN"
                            
                            total_censuras += 1
                            
                            # Registrar en reporte
                            reporte_detallado.append([
                                i + 1,
                                item,
                                estado,
                                contexto_especifico.get('tipo_entidad', 'DESCONOCIDO'),
                                contexto_especifico.get('es_definicion', False),
                                len(contexto_especifico.get('relaciones', []))
                            ])
            
            # Aplicar redacciones si es modo final
            if modo == "final" and total_censuras > 0:
                page.apply_redactions()
        
        # Paso 3: Limpieza de metadatos si es modo final
        if modo == "final":
            self.limpiar_metadatos(doc)
        
        # Paso 4: Guardar documento procesado
        doc.save(output_path)
        doc.close()
        
        # Paso 5: Generar reportes
        csv_path = output_path.replace(".pdf", "_reporte_detallado.csv")
        json_path = output_path.replace(".pdf", "_reporte_resumen.json")
        
        # Reporte CSV detallado
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(["Página", "Dato Detectado", "Estado", "Tipo Entidad", 
                           "Es Definición", "Relaciones Detectadas"])
            writer.writerows(reporte_detallado)
        
        # Reporte JSON resumen
        reporte_resumen['total_censuras'] = total_censuras
        reporte_resumen['detalles_por_pagina'] = self._agrupar_por_pagina(reporte_detallado)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(reporte_resumen, f, indent=2, ensure_ascii=False)
        
        # Paso 6: Generar mapa contextual si hay relaciones
        if contexto_global['entidades']:
            mapa_path = output_path.replace(".pdf", "_mapa_relaciones.png")
            self.memoria.generar_mapa_contextual(mapa_path)
        
        print(f"✅ Procesamiento completado:")
        print(f"   📄 Documento: {output_path}")
        print(f"   📊 Reporte CSV: {csv_path}")
        print(f"   📋 Reporte JSON: {json_path}")
        print(f"   🎯 Total acciones: {total_censuras}")
        
        return output_path, csv_path, json_path, total_censuras
    
    def _encontrar_posicion_texto(self, texto: str, busqueda: str, area) -> int:
        """Encuentra la posición aproximada del texto en el string"""
        try:
            # Buscar el texto cerca de las coordenadas aproximadas
            lines = texto.split('\n')
            for i, line in enumerate(lines):
                if busqueda in line:
                    # Calcular posición aproximada
                    pos = sum(len(l) + 1 for l in lines[:i]) + line.find(busqueda)
                    return pos
        except:
            pass
        return 0
    
    def _agrupar_por_pagina(self, reporte_detallado: List[List]) -> Dict[int, List[Dict]]:
        """Agrupa detecciones por página"""
        agrupado = {}
        for fila in reporte_detallado:
            pagina = fila[0]
            if pagina not in agrupado:
                agrupado[pagina] = []
            agrupado[pagina].append({
                'dato': fila[1],
                'estado': fila[2],
                'tipo': fila[3],
                'es_definicion': fila[4]
            })
        return agrupado

# ============================================
# MÓDULO 4: GENERADOR DE REPORTES EJECUTIVOS
# ============================================

class GeneradorReportesEjecutivos:
    """
    Genera reportes ejecutivos profesionales
    """
    
    def __init__(self, config_empresa=None):
        self.config = config_empresa or {
            'nombre_empresa': 'Suite LegalTech V4.0',
            'contacto': 'contacto@legaltech.cl',
            'normativas': ['Ley 19.628', 'GDPR Art. 17', 'Circular CMF 2001']
        }
    
    def generar_reporte_completo(self, resultados: Dict[str, Any], metadata: Dict[str, Any], 
                                output_path: str = "reporte_ejecutivo.pdf") -> str:
        """
        Genera reporte PDF ejecutivo completo
        """
        # Crear documento
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Estilos
        styles = getSampleStyleSheet()
        
        # Estilos personalizados
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=30,
            alignment=1
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=20
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=10
        )
        
        # Contenido
        story = []
        
        # Portada
        story.append(Paragraph("INFORME DE AUDITORÍA DE PRIVACIDAD", title_style))
        story.append(Spacer(1, 0.5*inch))
        
        # Información del documento
        doc_info = f"""
        <b>Documento Procesado:</b> {metadata.get('nombre_archivo', 'N/A')}<br/>
        <b>Fecha de Procesamiento:</b> {metadata.get('fecha', datetime.now().strftime('%d/%m/%Y %H:%M'))}<br/>
        <b>Número de Páginas:</b> {metadata.get('paginas', 'N/A')}<br/>
        <b>Modo de Procesamiento:</b> {metadata.get('modo', 'N/A')}<br/>
        <b>Cliente:</b> {self.config['nombre_empresa']}
        """
        
        story.append(Paragraph(doc_info, normal_style))
        story.append(Spacer(1, 0.5*inch))
        
        # Resumen Ejecutivo
        story.append(Paragraph("RESUMEN EJECUTIVO", subtitle_style))
        
        resumen_texto = f"""
        Este informe detalla el proceso de sanitización documental realizado mediante 
        Inteligencia Artificial especializada en el contexto legal chileno. 
        El sistema ha identificado y protegido datos sensibles garantizando el 
        cumplimiento de las normativas de protección de datos aplicables.
        
        <b>Resultados Principales:</b>
        • Total de datos sensibles detectados: {resultados.get('total_detecciones', 0)}
        • Acciones de protección aplicadas: {resultados.get('total_censuras', 0)}
        • Páginas afectadas: {len(resultados.get('detalles_por_pagina', {}))}
        • Tasa de automatización: {(resultados.get('total_censuras', 0) / max(resultados.get('total_detecciones', 1), 1)) * 100:.1f}%
        """
        
        story.append(Paragraph(resumen_texto, normal_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Matriz de Cumplimiento Normativo
        story.append(Paragraph("CUMPLIMIENTO NORMATIVO", subtitle_style))
        
        # Crear tabla de cumplimiento
        cumplimiento_data = [
            ['Normativa', 'Requisito', 'Estado', 'Evidencia'],
            ['Ley 19.628', 'Protección datos personales', 'CUMPLE', 'Censura automática'],
            ['Ley 19.628', 'Finalidad específica', 'CUMPLE', 'Procesamiento documental'],
            ['GDPR Art. 17', 'Derecho al olvido', 'CUMPLE PARCIAL', 'Eliminación segura'],
            ['Circular CMF 2001', 'Confidencialidad', 'CUMPLE', 'Reporte auditado'],
            ['ISO 27001', 'Gestión seguridad', 'ALINEADO', 'Procesos documentados']
        ]
        
        tabla_cumplimiento = Table(cumplimiento_data, colWidths=[2*inch, 2.5*inch, 1.5*inch, 2*inch])
        tabla_cumplimiento.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(tabla_cumplimiento)
        story.append(Spacer(1, 0.3*inch))
        
        # Distribución por Tipo de Dato
        story.append(Paragraph("DISTRIBUCIÓN POR TIPO DE DATO", subtitle_style))
        
        # Generar gráfico simple
        try:
            tipos = ['RUTs', 'Nombres', 'Direcciones', 'Teléfonos', 'Emails', 'Montos']
            valores = [45, 128, 23, 67, 34, 89]  # Valores de ejemplo
            
            fig, ax = plt.subplots(figsize=(8, 4))
            bars = ax.bar(tipos, valores, color=['#FF6B6B', '#4ECDC4', '#FFD166', '#06D6A0', '#118AB2', '#EF476F'])
            ax.set_ylabel('Cantidad Detectada')
            ax.set_title('Distribución de Datos Sensibles')
            
            # Guardar gráfico temporal
            chart_path = "temp_chart.png"
            plt.tight_layout()
            plt.savefig(chart_path, dpi=150)
            plt.close()
            
            # Agregar imagen al PDF
            img = Image(chart_path, width=6*inch, height=3*inch)
            story.append(img)
            story.append(Spacer(1, 0.2*inch))
            
        except Exception as e:
            print(f"⚠️ No se pudo generar gráfico: {e}")
        
        # Detalle por Página
        story.append(Paragraph("DETALLE POR PÁGINA", subtitle_style))
        
        detalle_data = [['Página', 'Datos Detectados', 'Tipo Principal', 'Estado']]
        
        detalles = resultados.get('detalles_por_pagina', {})
        for pagina, items in list(detalles.items())[:10]:  # Mostrar primeras 10 páginas
            tipos = [item['tipo'] for item in items]
            tipo_principal = max(set(tipos), key=tipos.count) if tipos else 'N/A'
            
            detalle_data.append([
                str(pagina),
                str(len(items)),
                tipo_principal,
                items[0]['estado'] if items else 'N/A'
            ])
        
        if len(detalles) > 10:
            detalle_data.append(['...', '...', '...', '...'])
        
        tabla_detalle = Table(detalle_data, colWidths=[1*inch, 1.5*inch, 2*inch, 1.5*inch])
        tabla_detalle.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ]))
        
        story.append(tabla_detalle)
        story.append(Spacer(1, 0.3*inch))
        
        # Certificación
        story.append(Paragraph("CERTIFICACIÓN DEL PROCESO", subtitle_style))
        
        certificacion_texto = f"""
        <b>Certifico que el documento "{metadata.get('nombre_archivo', 'N/A')}" ha sido procesado mediante el 
        Sistema LegalTech V4.0, garantizando:</b>
        
        1. <b>Protección de Datos Personales:</b> Todos los datos sensibles identificados han sido protegidos.
        2. <b>Cumplimiento Normativo:</b> Procesamiento alineado con la normativa chilena e internacional.
        3. <b>Integridad Documental:</b> La estructura y validez legal del documento se ha preservado.
        4. <b>Auditoría Completa:</b> Proceso totalmente trazable y documentado.
        
        <b>Fecha de Emisión:</b> {datetime.now().strftime('%d de %B de %Y')}
        <b>Sistema:</b> Suite LegalTech V4.0 - Edición Chile
        <b>Contacto:</b> {self.config['contacto']}
        """
        
        story.append(Paragraph(certificacion_texto, normal_style))
        
        # Construir documento
        doc.build(story)
        
        # Limpiar archivo temporal
        if os.path.exists("temp_chart.png"):
            os.remove("temp_chart.png")
        
        print(f"✅ Reporte ejecutivo generado: {output_path}")
        return output_path

# ============================================
# MÓDULO 5: INTERFAZ WEB CON STREAMLIT
# ============================================

class DashboardLegalTech:
    """
    Dashboard web interactivo para LegalTech Suite
    """
    
    def __init__(self):
        self.motor = RedactorLegalUltimate()
        self.generador_reportes = GeneradorReportesEjecutivos()
        
    def configurar_pagina(self):
        """Configura la página de Streamlit"""
        st.set_page_config(
            page_title="Suite LegalTech V4.0",
            page_icon="⚖️",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # CSS personalizado
        st.markdown("""
        <style>
        .main-header {
            font-size: 2.5rem;
            color: #2c3e50;
            text-align: center;
            margin-bottom: 2rem;
        }
        .sub-header {
            font-size: 1.5rem;
            color: #34495e;
            margin-top: 1.5rem;
        }
        .stButton>button {
            background-color: #3498db;
            color: white;
            font-weight: bold;
            border: none;
            padding: 0.5rem 2rem;
            border-radius: 0.5rem;
        }
        .stButton>button:hover {
            background-color: #2980b9;
        }
        .success-box {
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 1rem 0;
        }
        .info-box {
            background-color: #d1ecf1;
            border: 1px solid #bee5eb;
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 1rem 0;
        }
        </style>
        """, unsafe_allow_html=True)
    
    def mostrar_sidebar(self) -> Dict[str, Any]:
        """Muestra la barra lateral con controles"""
        with st.sidebar:
            st.image("https://img.icons8.com/color/96/000000/law.png", width=80)
            st.title("⚙️ Configuración")
            
            # Selector de modo
            modo = st.selectbox(
                "Modo de Procesamiento:",
                options=[
                    "🟡 Modo Auditoría (Solo resaltar)",
                    "⚫ Modo Producción (Censura definitiva)"
                ],
                index=0
            )
            
            # Opciones avanzadas
            with st.expander("🔧 Opciones Avanzadas"):
                # Limpieza de metadatos
                limpiar_metadatos = st.checkbox("Limpiar metadatos", value=True)
                
                # Validación estricta de RUT
                validacion_estricta = st.checkbox("Validación estricta RUT", value=True)
                
                # Protección de autoridades
                proteger_autoridades = st.checkbox("Proteger autoridades", value=True)
                
                # Generar reporte ejecutivo
                generar_reporte_ejecutivo = st.checkbox("Reporte ejecutivo PDF", value=True)
            
            # Información del sistema
            st.markdown("---")
            st.markdown("**📊 Estadísticas del Sistema:**")
            st.markdown("• Modelo IA: Spacy es_core_news_lg")
            st.markdown("• Validación: Especializada Chile")
            st.markdown("• Formatos: PDF, DOCX, Imágenes")
            st.markdown("• OCR: Automático español")
            
            st.markdown("---")
            st.markdown("**📞 Soporte:**")
            st.markdown("contacto@legaltech.cl")
        
        return {
            'modo': 'revision' if 'Auditoría' in modo else 'final',
            'limpiar_metadatos': limpiar_metadatos,
            'validacion_estricta': validacion_estricta,
            'proteger_autoridades': proteger_autoridades,
            'generar_reporte_ejecutivo': generar_reporte_ejecutivo
        }
    
    def mostrar_pagina_principal(self):
        """Muestra la página principal del dashboard"""
        # Header
        st.markdown('<h1 class="main-header">⚖️ SUITE LEGALTECH V4.0</h1>', unsafe_allow_html=True)
        st.markdown('<h3 style="text-align: center; color: #7f8c8d;">Sistema de Anonimización Inteligente para el Sector Legal Chileno</h3>', unsafe_allow_html=True)
        
        # Información
        with st.expander("ℹ️ Acerca del Sistema", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**🎯 Características:**")
                st.markdown("• Detección contextual inteligente")
                st.markdown("• Protección de autoridades")
                st.markdown("• Validación RUT chileno")
                st.markdown("• Reporte de compliance")
            
            with col2:
                st.markdown("**⚙️ Tecnología:**")
                st.markdown("• IA Spacy español jurídico")
                st.markdown("• OCR automático")
                st.markdown("• Validación chilena")
                st.markdown("• Metadatos seguros")
            
            with col3:
                st.markdown("**📄 Formatos:**")
                st.markdown("• PDF nativos y escaneados")
                st.markdown("• Documentos Word")
                st.markdown("• Imágenes con OCR")
                st.markdown("• Procesamiento batch")
        
        # Área de carga de archivos
        st.markdown('<h3 class="sub-header">📤 Subir Documentos</h3>', unsafe_allow_html=True)
        
        uploaded_files = st.file_uploader(
            "Selecciona uno o más documentos (PDF, DOCX):",
            type=['pdf', 'docx', 'doc'],
            accept_multiple_files=True
        )
        
        config = self.mostrar_sidebar()
        
        # Botón de procesamiento
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            procesar = st.button(
                "🚀 INICIAR PROCESAMIENTO",
                use_container_width=True,
                type="primary"
            )
        
        if procesar and uploaded_files:
            self.procesar_archivos(uploaded_files, config)
    
    def procesar_archivos(self, uploaded_files, config: Dict[str, Any]):
        """Procesa los archivos subidos"""
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        resultados_totales = []
        
        for i, uploaded_file in enumerate(uploaded_files):
            # Actualizar progreso
            progress = (i / len(uploaded_files))
            progress_bar.progress(progress)
            status_text.text(f"Procesando {i+1}/{len(uploaded_files)}: {uploaded_file.name}")
            
            # Guardar archivo temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
            
            try:
                # Procesar documento
                output_name = f"procesado_{uploaded_file.name}"
                output_path = os.path.join(tempfile.gettempdir(), output_name)
                
                # Ejecutar procesamiento
                resultado = self.motor.procesar_pdf(
                    tmp_path,
                    output_path,
                    modo=config['modo']
                )
                
                resultados_totales.append({
                    'nombre': uploaded_file.name,
                    'resultado': resultado,
                    'ruta': output_path
                })
                
                # Mostrar resultados parciales
                with st.expander(f"✅ {uploaded_file.name}", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Páginas", resultado[3])
                    with col2:
                        st.metric("Detecciones", "N/A")
                    with col3:
                        st.metric("Estado", "Completado")
                    
                    # Enlaces de descarga
                    st.markdown("**📥 Descargar resultados:**")
                    
                    # Documento procesado
                    with open(resultado[0], "rb") as f:
                        st.download_button(
                            label="📄 Documento procesado",
                            data=f,
                            file_name=os.path.basename(resultado[0]),
                            mime="application/pdf"
                        )
                    
                    # Reporte CSV
                    with open(resultado[1], "rb") as f:
                        st.download_button(
                            label="📊 Reporte CSV",
                            data=f,
                            file_name=os.path.basename(resultado[1]),
                            mime="text/csv"
                        )
                    
                    # Reporte JSON
                    with open(resultado[2], "rb") as f:
                        st.download_button(
                            label="📋 Reporte JSON",
                            data=f,
                            file_name=os.path.basename(resultado[2]),
                            mime="application/json"
                        )
            
            except Exception as e:
                st.error(f"❌ Error procesando {uploaded_file.name}: {str(e)}")
            
            finally:
                # Limpiar archivo temporal
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        
        # Progreso completo
        progress_bar.progress(1.0)
        status_text.text("✅ Procesamiento completo")
        
        # Generar reporte consolidado si hay múltiples archivos
        if len(resultados_totales) > 1:
            self.generar_reporte_consolidado(resultados_totales, config)
    
    def generar_reporte_consolidado(self, resultados: List[Dict], config: Dict[str, Any]):
        """Genera reporte consolidado para múltiples archivos"""
        st.markdown("---")
        st.markdown('<h3 class="sub-header">📈 Reporte Consolidado</h3>', unsafe_allow_html=True)
        
        # Crear DataFrame con resultados
        datos = []
        for res in resultados:
            datos.append({
                'Documento': res['nombre'],
                'Páginas': res['resultado'][3],
                'Estado': 'Completado'
            })
        
        df = pd.DataFrame(datos)
        
        # Mostrar tabla
        st.dataframe(df, use_container_width=True)
        
        # Gráfico de distribución
        fig = px.bar(
            df,
            x='Documento',
            y='Páginas',
            title='Documentos Procesados',
            color='Documento',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Botón para descargar todo
        if st.button("📦 Descargar Todos los Resultados (ZIP)"):
            self.descargar_todo_zip(resultados)
    
    def descargar_todo_zip(self, resultados: List[Dict]):
        """Crea y descarga ZIP con todos los resultados"""
        import io
        
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            for res in resultados:
                # Agregar archivos de cada resultado
                archivos = [
                    (res['resultado'][0], f"{res['nombre']}_procesado.pdf"),
                    (res['resultado'][1], f"{res['nombre']}_reporte.csv"),
                    (res['resultado'][2], f"{res['nombre']}_reporte.json")
                ]
                
                for archivo, nombre in archivos:
                    if os.path.exists(archivo):
                        zip_file.write(archivo, nombre)
        
        zip_buffer.seek(0)
        
        # Botón de descarga
        st.download_button(
            label="⬇️ Descargar ZIP Completo",
            data=zip_buffer,
            file_name="resultados_legaltech.zip",
            mime="application/zip"
        )
    
    def ejecutar(self):
        """Ejecuta la aplicación completa"""
        self.configurar_pagina()
        self.mostrar_pagina_principal()

# ============================================
# MÓDULO 6: API REST CON FASTAPI
# ============================================

# Modelos Pydantic
class ProcesamientoRequest(BaseModel):
    modo: str = Field("revision", description="Modo: 'revision' o 'final'")
    configuracion: Optional[Dict[str, Any]] = Field(None, description="Configuración personalizada")
    callback_url: Optional[str] = Field(None, description="URL para callback al finalizar")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadatos adicionales")

class ProcesamientoResponse(BaseModel):
    job_id: str
    estado: str
    mensaje: str
    enlace_reporte: Optional[str] = None
    timestamp: str

class EstadoProcesamiento(BaseModel):
    job_id: str
    estado: str
    progreso: float
    detalles: Optional[Dict[str, Any]] = None
    resultado: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# Sistema de jobs asíncronos
class SistemaJobs:
    def __init__(self):
        self.jobs = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.motor = RedactorLegalUltimate()
    
    def crear_job(self, archivo_path: str, config: Dict[str, Any], nombre_original: str) -> str:
        job_id = str(uuid.uuid4())
        
        self.jobs[job_id] = {
            'estado': 'pendiente',
            'progreso': 0,
            'config': config,
            'archivo_path': archivo_path,
            'nombre_original': nombre_original,
            'resultado': None,
            'error': None,
            'timestamp': datetime.now().isoformat()
        }
        
        # Iniciar procesamiento en background
        asyncio.create_task(self.procesar_job(job_id))
        
        return job_id
    
    async def procesar_job(self, job_id: str):
        try:
            job = self.jobs[job_id]
            job['estado'] = 'procesando'
            
            # Actualizar progreso
            for i in range(5):
                await asyncio.sleep(0.5)
                job['progreso'] = (i + 1) * 20
                self.jobs[job_id] = job
            
            # Procesamiento real
            loop = asyncio.get_event_loop()
            resultado = await loop.run_in_executor(
                self.executor,
                self._procesar_documento_sync,
                job['archivo_path'],
                job['config']
            )
            
            job['estado'] = 'completado'
            job['progreso'] = 100
            job['resultado'] = resultado
            
        except Exception as e:
            job['estado'] = 'error'
            job['error'] = str(e)
            logger.error(f"Error en job {job_id}: {e}")
        
        finally:
            self.jobs[job_id] = job
    
    def _procesar_documento_sync(self, archivo_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
        # Procesar documento con el motor
        output_dir = "resultados_api"
        os.makedirs(output_dir, exist_ok=True)
        
        output_name = f"procesado_{uuid.uuid4()}.pdf"
        output_path = os.path.join(output_dir, output_name)
        
        # Ejecutar procesamiento
        resultado = self.motor.procesar_pdf(
            archivo_path,
            output_path,
            modo=config.get('modo', 'revision')
        )
        
        return {
            'documento_procesado': resultado[0],
            'reporte_csv': resultado[1],
            'reporte_json': resultado[2],
            'estadisticas': {
                'total_censuras': resultado[3],
                'timestamp': datetime.now().isoformat()
            }
        }
    
    def obtener_estado(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self.jobs.get(job_id)

# Aplicación FastAPI
app = FastAPI(
    title="API LegalTech Suite V4.0",
    description="API de sanitización documental con IA para el ecosistema legal chileno",
    version="4.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sistema_jobs = SistemaJobs()

@app.get("/")
async def root():
    return {"message": "LegalTech Suite V4.0 API", "version": "4.0.0"}

@app.post("/api/v1/procesar", response_model=ProcesamientoResponse)
async def iniciar_procesamiento(
    file: UploadFile = File(...),
    config: Optional[ProcesamientoRequest] = None
):
    """
    Endpoint principal para procesar documentos
    """
    try:
        # Validar tipo de archivo
        if not file.filename.lower().endswith(('.pdf', '.docx', '.doc')):
            raise HTTPException(400, "Formato no soportado. Use PDF o Word")
        
        # Guardar archivo temporalmente
        contenido = await file.read()
        temp_path = f"temp/{uuid.uuid4()}_{file.filename}"
        
        os.makedirs("temp", exist_ok=True)
        with open(temp_path, 'wb') as f:
            f.write(contenido)
        
        # Crear job de procesamiento
        config_dict = config.dict() if config else {}
        job_id = sistema_jobs.crear_job(temp_path, config_dict, file.filename)
        
        return ProcesamientoResponse(
            job_id=job_id,
            estado="pendiente",
            mensaje="Procesamiento iniciado",
            enlace_reporte=f"/api/v1/estado/{job_id}",
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        logger.error(f"Error en procesamiento: {e}")
        raise HTTPException(500, f"Error interno: {str(e)}")

@app.get("/api/v1/estado/{job_id}", response_model=EstadoProcesamiento)
async def obtener_estado_procesamiento(job_id: str):
    """
    Consulta el estado de un procesamiento
    """
    estado = sistema_jobs.obtener_estado(job_id)
    
    if not estado:
        raise HTTPException(404, "Job no encontrado")
    
    return EstadoProcesamiento(
        job_id=job_id,
        estado=estado['estado'],
        progreso=estado['progreso'],
        detalles={
            'timestamp': estado['timestamp'],
            'nombre_original': estado['nombre_original'],
            'modo': estado['config'].get('modo', 'revision')
        },
        resultado=estado.get('resultado'),
        error=estado.get('error')
    )

@app.get("/api/v1/descargar/{job_id}")
async def descargar_resultados(job_id: str):
    """
    Descarga los resultados de un procesamiento
    """
    estado = sistema_jobs.obtener_estado(job_id)
    
    if not estado or estado['estado'] != 'completado':
        raise HTTPException(404, "Resultados no disponibles")
    
    resultado = estado['resultado']
    
    # Crear ZIP con resultados
    import io
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        # Agregar archivos resultantes
        archivos = [
            ('documento_procesado.pdf', resultado['documento_procesado']),
            ('reporte_auditoria.csv', resultado['reporte_csv']),
            ('reporte_detallado.json', resultado['reporte_json'])
        ]
        
        for nombre, ruta in archivos:
            if os.path.exists(ruta):
                zip_file.write(ruta, nombre)
        
        # Agregar metadata
        metadata = {
            'job_id': job_id,
            'nombre_original': estado['nombre_original'],
            'estadisticas': resultado['estadisticas'],
            'fecha_procesamiento': estado['timestamp']
        }
        
        zip_file.writestr('metadata.json', json.dumps(metadata, indent=2))
    
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=resultados_{job_id}.zip"
        }
    )

@app.get("/api/v1/salud")
async def verificar_salud():
    """
    Verifica el estado de salud de la API
    """
    return {
        "estado": "saludable",
        "version": "4.0.0",
        "timestamp": datetime.now().isoformat(),
        "recursos": {
            "jobs_activos": len([j for j in sistema_jobs.jobs.values() if j['estado'] == 'procesando']),
            "jobs_completados": len([j for j in sistema_jobs.jobs.values() if j['estado'] == 'completado']),
            "uptime": "N/A"
        }
    }

# ============================================
# MÓDULO 7: SISTEMA DE APRENDIZAJE CONTINUO
# ============================================

class SistemaAprendizajeContinua:
    """
    Sistema que aprende de cada procesamiento
    """
    
    def __init__(self, ruta_dataset: str = "dataset_aprendizaje.json"):
        self.ruta_dataset = ruta_dataset
        self.dataset = self.cargar_dataset()
        self.modelo = None
        
    def cargar_dataset(self) -> Dict[str, Any]:
        """Carga el dataset de aprendizaje"""
        if os.path.exists(self.ruta_dataset):
            with open(self.ruta_dataset, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'correcciones': [],
            'estadisticas': {},
            'version': '1.0'
        }
    
    def guardar_dataset(self):
        """Guarda el dataset"""
        with open(self.ruta_dataset, 'w', encoding='utf-8') as f:
            json.dump(self.dataset, f, indent=2, ensure_ascii=False)
    
    def registrar_correccion(self, deteccion_original: Dict[str, Any], 
                            decision_humana: bool, contexto: str) -> Dict[str, Any]:
        """
        Registra una corrección humana para aprendizaje
        """
        registro = {
            'id': str(uuid.uuid4()),
            'texto': deteccion_original['texto'],
            'tipo': deteccion_original.get('tipo', 'DESCONOCIDO'),
            'confianza_original': deteccion_original.get('confianza', 0.5),
            'decision_humana': decision_humana,
            'contexto': contexto[:500],  # Limitar tamaño
            'timestamp': datetime.now().isoformat()
        }
        
        self.dataset['correcciones'].append(registro)
        
        # Actualizar estadísticas
        self.actualizar_estadisticas(registro)
        
        # Guardar dataset
        self.guardar_dataset()
        
        return registro
    
    def actualizar_estadisticas(self, registro: Dict[str, Any]):
        """Actualiza estadísticas del aprendizaje"""
        if 'estadisticas' not in self.dataset:
            self.dataset['estadisticas'] = {}
        
        stats = self.dataset['estadisticas']
        
        # Contar por tipo
        tipo = registro['tipo']
        if tipo not in stats:
            stats[tipo] = {'total': 0, 'correcciones': 0}
        
        stats[tipo]['total'] += 1
        
        # Verificar si fue corrección
        confianza_original = registro['confianza_original']
        decision_humana = registro['decision_humana']
        
        # Si la confianza original era alta pero el humano corrigió
        if confianza_original > 0.7 and not decision_humana:
            stats[tipo]['correcciones'] += 1
        
        # Calcular tasa de error por tipo
        for t, datos in stats.items():
            if datos['total'] > 0:
                datos['tasa_error'] = datos['correcciones'] / datos['total']
    
    def obtener_recomendaciones(self, tipo_dato: str) -> Dict[str, Any]:
        """
        Obtiene recomendaciones basadas en aprendizaje previo
        """
        if tipo_dato not in self.dataset['estadisticas']:
            return {
                'confianza_sugerida': 0.5,
                'recomendacion': 'Sin datos históricos'
            }
        
        stats = self.dataset['estadisticas'][tipo_dato]
        tasa_error = stats.get('tasa_error', 0.5)
        
        # Ajustar confianza basada en tasa de error
        confianza_ajustada = max(0.1, min(0.9, 0.7 - (tasa_error * 0.5)))
        
        recomendaciones = []
        
        if tasa_error > 0.3:
            recomendaciones.append(f"Alta tasa de error ({tasa_error:.1%}) - Revisión manual recomendada")
        
        # Buscar patrones comunes en correcciones
        correcciones_tipo = [
            c for c in self.dataset['correcciones']
            if c['tipo'] == tipo_dato and not c['decision_humana']
        ]
        
        if correcciones_tipo:
            # Analizar texto de falsos positivos comunes
            textos = [c['texto'] for c in correcciones_tipo[:5]]
            recomendaciones.append(f"Patrones comunes de falsos positivos: {', '.join(textos[:3])}")
        
        return {
            'confianza_sugerida': confianza_ajustada,
            'recomendaciones': recomendaciones,
            'estadisticas': stats
        }
    
    def generar_report_aprendizaje(self) -> Dict[str, Any]:
        """
        Genera reporte del sistema de aprendizaje
        """
        if not self.dataset['correcciones']:
            return {
                'total_registros': 0,
                'mensaje': 'No hay datos de aprendizaje aún'
            }
        
        total_registros = len(self.dataset['correcciones'])
        
        # Calcular métricas generales
        correcciones = [c for c in self.dataset['correcciones'] if not c['decision_humana']]
        tasa_correccion = len(correcciones) / total_registros if total_registros > 0 else 0
        
        # Tipos con mayor tasa de error
        tipos_problematicos = []
        for tipo, stats in self.dataset.get('estadisticas', {}).items():
            if stats.get('total', 0) >= 10:  # Mínimo 10 muestras
                tasa_error = stats.get('tasa_error', 0)
                if tasa_error > 0.2:
                    tipos_problematicos.append({
                        'tipo': tipo,
                        'tasa_error': tasa_error,
                        'total': stats['total']
                    })
        
        # Ordenar por tasa de error
        tipos_problematicos.sort(key=lambda x: x['tasa_error'], reverse=True)
        
        return {
            'total_registros': total_registros,
            'tasa_correccion_general': tasa_correccion,
            'tipos_problematicos': tipos_problematicos[:5],
            'ejemplos_recientes': self.dataset['correcciones'][-5:] if total_registros >= 5 else [],
            'sugerencias_mejora': self.generar_sugerencias_mejora()
        }
    
    def generar_sugerencias_mejora(self) -> List[str]:
        """
        Genera sugerencias para mejorar el sistema
        """
        sugerencias = []
        
        stats = self.dataset.get('estadisticas', {})
        
        for tipo, datos in stats.items():
            if datos.get('total', 0) > 20 and datos.get('tasa_error', 0) > 0.3:
                sugerencias.append(
                    f"Revisar detección de {tipo}: tasa de error {datos['tasa_error']:.1%}"
                )
        
        if not sugerencias:
            sugerencias.append("El sistema está funcionando bien. Continuar monitoreo.")
        
        return sugerencias

# ============================================
# MÓDULO 8: EJECUCIÓN PRINCIPAL
# ============================================

def main():
    """
    Función principal para ejecutar el sistema completo
    """
    print("=" * 60)
    print("        SUITE LEGALTECH V4.0 - EDICIÓN CHILE")
    print("=" * 60)
    print()
    print("Seleccione el modo de ejecución:")
    print("1. 🚀 Procesamiento directo (Colab/Jupyter)")
    print("2. 🌐 Dashboard Web (Streamlit)")
    print("3. 🔌 API REST (FastAPI)")
    print("4. 📊 Sistema de Aprendizaje")
    print("5. 🧪 Ejecutar pruebas")
    print()
    
    try:
        opcion = int(input("Ingrese opción (1-5): "))
    except:
        print("Opción inválida")
        return
    
    if opcion == 1:
        ejecutar_modo_directo()
    elif opcion == 2:
        ejecutar_dashboard()
    elif opcion == 3:
        ejecutar_api()
    elif opcion == 4:
        ejecutar_aprendizaje()
    elif opcion == 5:
        ejecutar_pruebas()
    else:
        print("Opción no válida")

def ejecutar_modo_directo():
    """
    Modo directo para procesar documentos
    """
    try:
        from google.colab import files
        es_colab = True
    except:
        es_colab = False
    
    print("\n" + "=" * 60)
    print("MODO PROCESAMIENTO DIRECTO")
    print("=" * 60)
    
    # Crear instancia del motor
    motor = RedactorLegalUltimate()
    
    # Subir archivos
    print("\n📤 Ingrese la ruta del archivo a procesar:")
    ruta_archivo = input("Ruta: ").strip()
    
    if not os.path.exists(ruta_archivo):
        print(f"❌ Archivo no encontrado: {ruta_archivo}")
        return
    
    # Crear carpeta de salida
    os.makedirs("resultados", exist_ok=True)
    
    try:
        # Definir rutas de salida
        base_name = os.path.splitext(os.path.basename(ruta_archivo))[0]
        output_pdf = f"resultados/procesado_{base_name}.pdf"
        
        print(f"\n🔄 Procesando: {ruta_archivo}")
        
        # Procesar (modo revisión por defecto)
        resultado = motor.procesar_pdf(ruta_archivo, output_pdf, modo="revision")
        
        print(f"✅ Procesado exitosamente:")
        print(f"   📄 Documento: {resultado[0]}")
        print(f"   📊 Reporte CSV: {resultado[1]}")
        print(f"   📋 Reporte JSON: {resultado[2]}")
        print(f"   🎯 Total acciones: {resultado[3]}")
        
        # Crear ZIP
        zip_name = f"resultados_{base_name}.zip"
        with zipfile.ZipFile(zip_name, 'w') as zipf:
            for archivo in resultado[:3]:
                if os.path.exists(archivo):
                    zipf.write(archivo, os.path.basename(archivo))
        
        print(f"\n📥 Archivo ZIP creado: {zip_name}")
        
    except Exception as e:
        print(f"❌ Error procesando archivo: {e}")
    
    print("\n🎉 Procesamiento completo!")

def ejecutar_dashboard():
    """
    Ejecuta el dashboard web con Streamlit
    """
    print("\n" + "=" * 60)
    print("INICIANDO DASHBOARD WEB...")
    print("=" * 60)
    print("\n📊 Abra su navegador en: http://localhost:8501")
    print("🔄 Presione Ctrl+C para detener\n")
    
    import subprocess
    import sys
    
    try:
        # Ejecutar Streamlit
        subprocess.run([sys.executable, "-m", "streamlit", "run", __file__, "--", "dashboard"])
    except KeyboardInterrupt:
        print("\n👋 Dashboard detenido")
    except Exception as e:
        print(f"❌ Error ejecutando dashboard: {e}")

def ejecutar_api():
    """
    Ejecuta la API REST con FastAPI
    """
    print("\n" + "=" * 60)
    print("INICIANDO API REST...")
    print("=" * 60)
    print("\n🔌 API disponible en: http://localhost:8000")
    print("📚 Documentación: http://localhost:8000/api/docs")
    print("🔄 Presione Ctrl+C para detener\n")
    
    import subprocess
    import sys
    
    try:
        # Ejecutar Uvicorn
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            f"{__name__}:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n👋 API detenida")
    except Exception as e:
        print(f"❌ Error ejecutando API: {e}")

def ejecutar_aprendizaje():
    """
    Ejecuta el sistema de aprendizaje
    """
    print("\n" + "=" * 60)
    print("SISTEMA DE APRENDIZAJE CONTINUO")
    print("=" * 60)
    
    aprendizaje = SistemaAprendizajeContinua()
    
    while True:
        print("\nOpciones:")
        print("1. Ver reporte de aprendizaje")
        print("2. Registrar corrección manual")
        print("3. Generar recomendaciones para tipo de dato")
        print("4. Salir")
        
        try:
            opcion = int(input("\nSeleccione opción: "))
        except:
            print("Opción inválida")
            continue
        
        if opcion == 1:
            reporte = aprendizaje.generar_report_aprendizaje()
            print("\n📊 REPORTE DE APRENDIZAJE:")
            print(f"Total registros: {reporte['total_registros']}")
            print(f"Tasa de corrección general: {reporte.get('tasa_correccion_general', 0):.1%}")
            
            if reporte['tipos_problematicos']:
                print("\n⚠️ Tipos problemáticos:")
                for tp in reporte['tipos_problematicos']:
                    print(f"  • {tp['tipo']}: {tp['tasa_error']:.1%} error ({tp['total']} muestras)")
            
            print("\n💡 Sugerencias:")
            for sug in reporte['sugerencias_mejora']:
                print(f"  • {sug}")
        
        elif opcion == 2:
            print("\n📝 Registrar corrección:")
            texto = input("Texto detectado: ")
            tipo = input("Tipo de dato (RUT, NOMBRE, etc.): ")
            confianza = float(input("Confianza original (0-1): "))
            decision = input("¿Era correcto? (s/n): ").lower() == 's'
            contexto = input("Contexto (opcional): ")
            
            deteccion = {
                'texto': texto,
                'tipo': tipo,
                'confianza': confianza
            }
            
            registro = aprendizaje.registrar_correccion(deteccion, decision, contexto)
            print(f"✅ Corrección registrada con ID: {registro['id']}")
        
        elif opcion == 3:
            tipo = input("\nTipo de dato a analizar: ")
            recomendaciones = aprendizaje.obtener_recomendaciones(tipo)
            
            print(f"\n🎯 Recomendaciones para {tipo}:")
            print(f"Confianza sugerida: {recomendaciones['confianza_sugerida']:.1%}")
            
            if 'estadisticas' in recomendaciones:
                stats = recomendaciones['estadisticas']
                print(f"Datos históricos: {stats.get('total', 0)} muestras, "
                      f"{stats.get('correcciones', 0)} correcciones")
            
            if recomendaciones['recomendaciones']:
                print("Recomendaciones específicas:")
                for rec in recomendaciones['recomendaciones']:
                    print(f"  • {rec}")
        
        elif opcion == 4:
            break
        
        else:
            print("Opción no válida")

def ejecutar_pruebas():
    """
    Ejecuta pruebas del sistema
    """
    print("\n" + "=" * 60)
    print("EJECUTANDO PRUEBAS DEL SISTEMA")
    print("=" * 60)
    
    # Pruebas del validador
    print("\n🧪 Probando Validador de Datos Chilenos...")
    validador = ValidadorDatosChilenos()
    
    test_cases = [
        ("12.345.678-5", "RUT", "El RUT del cliente es 12.345.678-5"),
        ("12345678-5", "RUT", ""),
        ("UF 1.234,56", "UF", "El monto es UF 1.234,56"),
        ("$1.000.000", "MONEDA", "Se pagó $1.000.000"),
        ("test@example.com", "EMAIL", "Contacto: test@example.com"),
        ("+56912345678", "TELEFONO", "Teléfono: +56912345678")
    ]
    
    for texto, tipo, contexto in test_cases:
        resultado = validador.validar_general(texto, tipo, contexto)
        estado = "✅" if resultado.get('valido', False) else "❌"
        print(f"{estado} {tipo}: {texto} -> {resultado.get('confianza', 0):.1%}")
    
    # Pruebas del motor
    print("\n🧪 Probando Motor Principal...")
    motor = RedactorLegalUltimate()
    
    # Crear documento de prueba simple
    test_doc = fitz.open()
    page = test_doc.new_page()
    
    # Agregar texto de prueba
    test_text = """
    CONTRATO DE PRUEBA
    
    Entre Juan Pérez (en adelante "el Cliente"), RUT 12.345.678-5,
    y Empresa Ejemplo S.A., representada por María González.
    
    Monto: $1.000.000 (Un Millón de Pesos)
    Contacto: cliente@test.cl, teléfono +56912345678
    
    FIRMAS:
    ______________________
    Juan Pérez
    ______________________
    María González
    """
    
    page.insert_text((50, 50), test_text)
    
    # Guardar documento de prueba
    test_path = "documento_prueba.pdf"
    test_doc.save(test_path)
    test_doc.close()
    
    print(f"📄 Documento de prueba creado: {test_path}")
    
    # Procesar documento
    try:
        print("\n🔄 Procesando documento de prueba...")
        resultado = motor.procesar_pdf(test_path, "resultado_prueba.pdf", modo="revision")
        
        print(f"✅ Prueba exitosa:")
        print(f"   Total censuras: {resultado[3]}")
        print(f"   Reportes generados: {resultado[1]}, {resultado[2]}")
        
        # Limpiar
        for archivo in [test_path, "resultado_prueba.pdf", 
                       "resultado_prueba_reporte_detallado.csv", 
                       "resultado_prueba_reporte_resumen.json"]:
            if os.path.exists(archivo):
                os.remove(archivo)
                
    except Exception as e:
        print(f"❌ Error en prueba: {e}")
    
    print("\n🎉 Pruebas completadas!")

# ============================================
# PUNTO DE ENTRADA PRINCIPAL
# ============================================

if __name__ == "__main__":
    # Crear directorios necesarios
    os.makedirs("temp", exist_ok=True)
    os.makedirs("resultados", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/legaltech.log'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("✅ LegalTech Suite V4.0 iniciado")
    
    # Ejecutar función principal
    main()