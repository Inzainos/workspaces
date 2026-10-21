"""Shim de compatibilidad (2026-10-20): la validación de plausibilidad es un
INVARIANTE DE DOMINIO (rangos físicos), y core/ no debe importar de
infrastructure/ (Cosmic Python, DDD — la skill del ~/conocimiento). El
módulo vivo es core/plausibilidad.py; los fetchers (adaptadores) importan
desde aquí o desde core indistintamente.
"""
from sentinel_omega.core.plausibilidad import RANGOS, validar  # noqa: F401
