"""
pipeline.py
Procesa un grupo de 3 signos zodiacales, los sube a YouTube y a Google Drive.
Make.com detecta los archivos en Drive y los publica en TikTok automáticamente.

Uso:
  python pipeline.py --group 0   # Aries, Tauro, Géminis
  python pipeline.py --group 1   # Cáncer, Leo, Virgo
  python pipeline.py --group 2   # Libra, Escorpio, Sagitario
  python pipeline.py --group 3   # Capricornio, Acuario, Piscis
  python pipeline.py --group 0 --dry-run   # solo genera, no sube
  python pipeline.py --group 0 --cta paid  # con CTA de pago
  python pipeline.py --group 0 --cta free  # con CTA gratuita
  python pipeline.py --group 0 --cta none  # sin CTA extra
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import