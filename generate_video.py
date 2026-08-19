"""
generate_video.py
Genera videos de tarot por signo zodiacal (YouTube Shorts / TikTok 9:16, 720p).
Optimizado con la URL visible desde el fotograma 0 para máxima conversión en perfil.

Stack:
  - Groq (openai/gpt-oss-120b) → guión personalizado y extendido por signo (con respaldo robusto)
  - Google Cloud TTS         → voz en español Neural2
  - Pexels API               → fondo específico por carta
  - MoviePy + PIL            → composición 720x1280 (720p Shorts)

Estética: paleta de tarotgratis.online
"""

import PIL.Image as _pil_img
if not hasattr(_pil_img, 'ANTIALIAS'):
    _pil_img.ANTIALIAS = _pil_img.LANCZOS

import os
import json
import random
from datetime import datetime
from pathlib import Path

import requests
import numpy as np
from groq import Groq
from google.cloud import texttospeech
from moviepy.editor import (
    VideoFileClip, AudioFileClip, CompositeVideoClip,
    ImageClip, ColorClip, concatenate_videoclips,
)
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

load_dotenv()

# ── Resolución 720p (Shorts / TikTok 9:16) ────────────────────────────────────
VIDEO_W    = 720
VIDEO_H    = 1280
FPS        = 24
OUTPUT_DIR = Path("output_videos")
TEMP_DIR   = Path("temp")

# ── Paleta tarotgratis.online ─────────────────────────────────────────────────
C_BG_DEEP    = (30, 20, 59)
C_BG_MID     = (45, 30, 87)
C_GOLD       = (201, 168, 76)
C_GOLD_LIGHT = (240, 208, 128)
C_PURPLE     = (130, 43, 189)
C_PURPLE_L   = (182, 109, 248)
C_TEAL       = (15, 171, 162)
C_TEXT       = (253, 248, 240)
C_MUTED      = (160, 147, 176)

# ── Signos zodiacales ─────────────────────────────────────────────────────────
SIGNOS = [
    {"nombre": "Aries",       "emoji": "♈", "fechas": "21 mar – 19 abr"},
    {"nombre": "Tauro",       "emoji": "♉", "fechas": "20 abr – 20 may"},
    {"nombre": "Géminis",     "emoji": "♊", "fechas": "21 may – 20 jun"},
    {"nombre": "Cáncer",      "emoji": "♋", "fechas": "21 jun – 22 jul"},
    {"nombre": "Leo",         "emoji": "♌", "fechas": "23 jul – 22 ago"},
    {"nombre": "Virgo",       "emoji": "♍", "fechas": "23 ago – 22 sep"},
    {"nombre": "Libra",       "emoji": "♎", "fechas": "23 sep – 22 oct"},
    {"nombre": "Escorpio",    "emoji": "♏", "fechas": "23 oct – 21 nov"},
    {"nombre": "Sagitario",   "emoji": "♐", "fechas": "22 nov – 21 dic"},
    {"nombre": "Capricornio", "emoji": "♑", "fechas": "22 dic – 19 ene"},
    {"nombre": "Acuario",     "emoji": "♒", "fechas": "20 ene – 18 feb"},
    {"nombre": "Piscis",      "emoji": "♓", "fechas": "19 feb – 20 mar"},
]

# ── Arcanos mayores ───────────────────────────────────────────────────────────
ARCANOS = [
    "El Loco", "El Mago", "La Sacerdotisa", "La Emperatriz", "El Emperador",
    "El Hierofante", "Los Enamorados", "El Carro", "La Fuerza", "El Ermitaño",
    "La Rueda de la Fortuna", "La Justicia", "El Colgado", "La Muerte",
    "La Templanza", "El Diablo", "La Torre", "La Estrella", "La Luna",
    "El Sol", "El Juicio", "El Mundo",
]

CARD_GLYPHS = {
    "El Loco": "🎭", "El Mago": "⚡", "La Sacerdotisa": "🌙",
    "La Emperatriz": "🌿", "El Emperador": "👑", "El Hierofante": "🕊️",
    "Los Enamorados": "💫", "El Carro": "⚔️", "La Fuerza": "🦁",
    "El Ermitaño": "🕯️", "La Rueda de la Fortuna": "☸️", "La Justicia": "⚖️",
    "El Colgado": "💧", "La Muerte": "🌑", "La Templanza": "✨",
    "El Diablo": "🔥", "La Torre": "⚡", "La Estrella": "⭐",
    "La Luna": "🌙", "El Sol": "☀️", "El Juicio": "🎺", "El Mundo": "🌍",
}

CARD_PEXELS = {
    "El Loco":               ["adventure path nature", "freedom road", "leap cliff"],
    "El Mago":               ["mystical candle purple", "magic ritual dark", "crystal ball"],
    "La Sacerdotisa":        ["moon night purple", "mystery veil", "moonlight dark"],
    "La Emperatriz":         ["nature green abundance", "flowers garden", "earth goddess"],
    "El Emperador":          ["mountain peak", "stone throne", "power dark sky"],
    "El Hierofante":         ["ancient temple", "spiritual ceremony", "sacred candle"],
    "Los Enamorados":        ["couple sunset", "heart light bokeh", "love romance"],
    "El Carro":              ["road ahead night", "speed motion blur", "triumph victory"],
    "La Fuerza":             ["lion majestic", "strength nature", "powerful animal"],
    "La Ermitaño":           ["lantern night dark", "solitude path fog", "mystical forest"],
    "La Rueda de la Fortuna":["spinning stars galaxy", "cosmic wheel", "universe rotation"],
    "La Justicia":           ["scales balance", "law justice", "symmetry architecture"],
    "La Colgado":            ["water reflection", "hanging tree", "peaceful surrender"],
    "La Muerte":             ["autumn leaves falling", "transformation dark", "rebirth nature"],
    "La Templanza":          ["water pour light", "balance zen", "flowing river"],
    "El Diablo":             ["fire dark flames", "smoke dramatic", "red dark abstract"],
    "La Torre":              ["lightning storm dramatic", "tower dark", "storm clouds"],
    "La Estrella":           ["night sky stars", "galaxy milky way", "star field purple"],
    "La Luna":               ["full moon night", "moon reflection water", "lunar mystical"],
    "El Sol":                ["sunrise golden", "sunlight rays", "bright sun nature"],
    "La Juicio":             ["sunrise dramatic", "awakening light", "epic sky clouds"],
    "La Mundo":              ["earth globe space", "world complete", "universe harmony"],
}

DEFAULT_QUERIES = ["mystical dark purple", "night sky stars", "smoke dark background"]


def get_card_for_sign(signo_idx: int) -> str:
    hoy = datetime.now()
    idx = (hoy.year + hoy.month + hoy.day + signo_idx * 7) % len(ARCANOS)
    return ARCANOS[idx]


def _load_fonts(size_large, size_medium, size_small):
    bold_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "C:/Windows/Fonts/georgiab.ttf",
        "C:/Windows/Fonts/timesbd.ttf",
    ]
    reg_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "C:/Windows/Fonts/georgia.ttf",
        "C:/Windows/Fonts/times.ttf",
    ]
    def try_load(paths, size):
        for p in paths:
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
        return ImageFont.load_default()
    return (
        try_load(bold_candidates, size_large),
        try_load(bold_candidates, size_medium),
        try_load(reg_candidates, size_small),
    )


# ── Guión extendido con Groq (openai/gpt-oss-120b) y respaldo garantizado ──────
def generate_reading(signo: dict, card: str) -> dict:
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    hoy = datetime.now().strftime("%d de %B de %Y")

    prompt = f"""Eres la voz del Oráculo del Tarot. Generá un guión extenso y detallado para un YouTube Short de tarot para {signo['nombre']} con la carta "{card}".

Devolvé UNICAMENTE un objeto JSON válido con estas claves exactas (sin bloques de código markdown, sin comillas invertidas extra):
{{
  "title": "{signo['nombre'].upper()} HOY | {card} | Tarot {hoy}",
  "script": "Escribí un texto fluido de al menos 90 a 110 palabras en español. Hablá sobre el amor, la energía del día y un consejo profundo. Terminá estrictamente con la frase: Para tu lectura completa y personalizada, totalmente gratis, visitá tarotgratis punto online",
  "description": "Tarot de hoy para {signo['nombre']} 🔮",
  "tags": ["tarot", "{signo['nombre'].lower()}", "tarot diario"]
}}"""

    resp = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=900,
    )
    raw = resp.choices[0].message.content.strip()
    print("Respuesta cruda de Groq:", raw[:200])
    
    clean_raw = raw.replace("```json", "").replace("