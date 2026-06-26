"""
Shadow Node Theory (SNT) Core Engine
R(t) = a · t^b — Power Law Satellization Model

Author: Elán Zainos Corona (Fractal Core Research)
Version: v29 — 721 verified cases across 11 domains
"""

from .satellization import SatellizationEngine
from .friction import InstitutionalFrictionCalculator
from .asi import AtomicSovereigntyIndex
from .nbody import NBodyMatrix

__all__ = [
    "SatellizationEngine",
    "InstitutionalFrictionCalculator",
    "AtomicSovereigntyIndex",
    "NBodyMatrix",
]
