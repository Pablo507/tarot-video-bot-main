"""
generate_video.py
v6.0 — Layouts rompe-plantillas, Cartas reales, Gancho a Web Gratis.
"""

import PIL.Image as _pil_img
if not hasattr(_pil_img, 'ANTIALIAS'):
    _pil_img.ANTIALIAS = _pil_img.LANCZOS

import os
import json
import random
import hashlib
import time
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

VIDEO_W    = 720
VIDEO_H    = 1280
FPS        = 24
OUTPUT_DIR = Path("output_videos")
TEMP_DIR   = Path("temp")

C_BG_DEEP    = (30, 20, 59)
C_BG_MID     = (45, 30, 87)
C_GOLD       = (201, 168, 76)
C_GOLD_LIGHT = (240, 208, 128)
C_PURPLE     = (130, 43, 189)
C_PURPLE_L   = (182, 109, 248)
C_TEAL       = (15, 171, 162)
C_TEXT       = (253, 248, 240)
C_MUTED      = (160, 147, 176)
C_RED_ALERT  = (220, 60, 60)

# 5 Layouts TOTALMENTE diferentes
LAYOUT_STYLES = ["TOP_TEXT", "CENTER_BOX", "BOTTOM_TEXT", "FULL_IMPACT", "MINIMAL_CARD"]

TAROT_MEANINGS = {
    "El Loco": "nuevos comienzos, dar un salto de fe, libertad, espontaneidad",
    "El Mago": "poder personal, manifestación, habilidades, acción",
    "La Sacerdotisa": "intuición, secretos, sabiduría interior, paciencia",
    "La Emperatriz": "abundancia, creatividad, fertilidad, cuidado",
    "El Emperador": "estructura, autoridad, control, estabilidad",
    "El Hierofante": "tradición, guía espiritual, reglas, aprendizaje",
    "Los Enamorados": "relaciones, elecciones, alineación de valores, amor",
    "El Carro": "voluntad, determinación, victoria, control del destino",
    "La Fuerza": "coraje interior, compasión, paciencia, control de impulsos",
    "El Ermitaño": "introspección, soledad, buscar la verdad, guía interior",
    "La Rueda de la Fortuna": "cambios, ciclos, destino, giros inesperados",
    "La Justicia": "verdad, causa y efecto, equilibrio, decisiones justas",
    "El Colgado": "pausa, rendición, dejar ir, nueva perspectiva",
    "La Muerte": "transformación profunda, finales, renacimiento",
    "La Templanza": "equilibrio, moderación, sanación, paciencia",
    "El Diablo": "tentación, ataduras, sombra, deseo material",
    "La Torre": "ruptura, caos, revelación, reconstrucción",
    "La Estrella": "esperanza, inspiración, sanación, fe en el futuro",
    "La Luna": "ilusión, miedo, subconsciente, confusión",
    "El Sol": "éxito, alegría, vitalidad, claridad",
    "El Juicio": "despertar, juicio, renacimiento, perdón",
    "El Mundo": "culminación, éxito, logros, plenitud",
}

SCRIPT_STRUCTURES = ["PREGUNTA_DIRECTA", "ESCENA_SENSORIAL", "AFIRMACION_FUERTE", "NOMBRE_DIRECTO", "CONTRASTE"]
CTA_COMMENT = "Contame en los comentarios si esto te resuena hoy."
CTA_SAVE = "Guardá este video en favoritos para volver a verlo cuando lo necesites."

# CAMBIO DE ESTRATEGIA: Ofrecer algo GRATIS para que entren a la web
CTA_HOOK = "Si querés saber qué te depara el destino, entrá ahora a tarotgratis.online."
CTA_FINAL = "Sacá tu carta del tarot GRATIS por tiempo limitado en tarotgratis.online. Sin registro, solo entrás y te lees la suerte."

HOOK_PHRASES = [
    "¿POR QUÉ TE SENTÍS ASÍ?", "ESTO NO ES CASUALIDAD", "DEJÁ DE HACER ESTO HOY",
    "ESTO TE VA A DOLER", "CUIDADO", "EL ERROR QUE COMETÉS",
    "NADIE TE DIJO ESTO", "TENÉS HASTA HOY"
]

SIGN_CARD_OFFSETS = [0, 7, 14, 3, 10, 17, 4, 11, 18, 5, 12, 19]

SIGNOS = [
    {"nombre": "Aries", "elemento": "Fuego", "tono": "impulsivo, directo", "temas": ["acción inmediata", "liderazgo", "coraje", "paciencia"]},
    {"nombre": "Tauro", "elemento": "Tierra", "tono": "sensual, estable", "temas": ["seguridad material", "placeres simples", "constancia", "soltar"]},
    {"nombre": "Géminis", "elemento": "Aire", "tono": "curioso, disperso", "temas": ["comunicación", "aprendizaje", "decisiones", "elegir"]},
    {"nombre": "Cáncer", "elemento": "Agua", "tono": "emocional, protector", "temas": ["familia", "hogar", "sanar", "límites"]},
    {"nombre": "Leo", "elemento": "Fuego", "tono": "dramático, orgulloso", "temas": ["brillar", "creatividad", "reconocimiento", "humildad"]},
    {"nombre": "Virgo", "elemento": "Tierra", "tono": "analítico, servicial", "temas": ["orden", "salud", "servicio", "soltar perfeccionismo"]},
    {"nombre": "Libra", "elemento": "Aire", "tono": "diplomático, indeciso", "temas": ["relaciones", "belleza", "equilibrio", "decidir"]},
    {"nombre": "Escorpio", "elemento": "Agua", "tono": "intenso, reservado", "temas": ["transformación", "poder personal", "celos", "confiar"]},
    {"nombre": "Sagitario", "elemento": "Fuego", "tono": "aventurero, exagerado", "temas": ["expansión", "viajes", "fe", "compromiso"]},
    {"nombre": "Capricornio", "elemento": "Tierra", "tono": "disciplinado, frío", "temas": ["metas", "responsabilidad", "trabajo", "disfrutar"]},
    {"nombre": "Acuario", "elemento": "Aire", "tono": "rebelde, distante", "temas": ["libertad", "innovación", "amistades", "emociones"]},
    {"nombre": "Piscis", "elemento": "Agua", "tono": "soñador, evasivo", "temas": ["intuición", "arte", "espiritualidad", "límites"]},
]

ARCANOS = ["El Loco", "El Mago", "La Sacerdotisa", "La Emperatriz", "El Emperador", "El Hierofante", "Los Enamorados", "El Carro", "La Fuerza", "El Ermitaño", "La Rueda de la Fortuna", "La Justicia", "El Colgado", "La Muerte", "La Templanza", "El Diablo", "La Torre", "La Estrella", "La Luna", "El Sol", "El Juicio", "El Mundo"]
CARD_PEXELS = {"El Loco": ["adventure path", "freedom road"], "El Mago": ["candle purple", "magic ritual"], "La Sacerdotisa": ["moon night", "mystery veil"], "La Emperatriz": ["nature abundance", "flowers"], "El Emperador": ["mountain peak", "stone throne"], "El Hierofante": ["ancient temple", "sacred candle"], "Los Enamorados": ["couple sunset", "love romance"], "El Carro": ["road night", "speed motion"], "La Fuerza": ["lion majestic", "powerful animal"], "La Ermitaño": ["lantern dark", "solitude path"], "La Rueda de la Fortuna": ["spinning stars", "cosmic wheel"], "La Justicia": ["scales balance", "symmetry architecture"], "La Colgado": ["water reflection", "hanging tree"], "La Muerte": ["autumn leaves", "transformation dark"], "La Templanza": ["water pour", "balance zen"], "El Diablo": ["dark flames", "smoke dramatic"], "La Torre": ["lightning storm", "tower dark"], "La Estrella": ["night sky stars", "galaxy milky"], "La Luna": ["full moon", "moon reflection"], "El Sol": ["sunrise golden", "sunlight rays"], "La Juicio": ["sunrise dramatic", "awakening light"], "La Mundo": ["earth globe", "universe harmony"]}
DEFAULT_QUERIES = ["mystical dark purple", "night sky stars", "smoke dark background"]
VOCES_POR_ELEMENTO = {"Fuego": "es-US-Neural2-A", "Tierra": "es-US-Neural2-A", "Aire": "es-US-Journey-F", "Agua": "es-US-Neural2-A"}
VOCES_SIN_PITCH = {"es-US-Journey-F", "es-US-Journey-D", "es-US-Journey-O"}
_BOLD_FONT_PATHS = ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf", "C:/Windows/Fonts/georgiab.ttf", "C:/Windows/Fonts/timesbd.ttf"]

def get_card_for_sign(signo_idx: int) -> str:
    hoy = datetime.now()
    day_offset = (hoy.year * 31 + hoy.month * 17 + hoy.day) % len(ARCANOS)
    idx = (day_offset + SIGN_CARD_OFFSETS[signo_idx]) % len(ARCANOS)
    return ARCANOS[idx]

def _load_fonts(size_large, size_medium, size_small):
    reg_candidates = ["/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", "C:/Windows/Fonts/georgia.ttf"]
    def try_load(paths, size):
        for p in paths:
            try: return ImageFont.truetype(p, size)
            except: continue
        return ImageFont.load_default()
    return (try_load(_BOLD_FONT_PATHS, size_large), try_load(_BOLD_FONT_PATHS, size_medium), try_load(reg_candidates, size_small))

def _fit_font_to_width(text: str, max_width: int, initial_size: int, min_size: int = 36):
    size = initial_size
    while size > min_size:
        font = None
        for p in _BOLD_FONT_PATHS:
            try: font = ImageFont.truetype(p, size); break
            except: continue
        if font is None: return ImageFont.load_default()
        bbox = font.getbbox(text)
        if bbox[2] - bbox[0] <= max_width: return font
        size -= 2
    return ImageFont.truetype(_BOLD_FONT_PATHS[0], min_size) if os.path.exists(_BOLD_FONT_PATHS[0]) else ImageFont.load_default()

def generate_reading(signo: dict, card: str) -> dict:
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    hoy = datetime.now().strftime("%d de %B de %Y")
    significado_carta = TAROT_MEANINGS.get(card, "transformación y crecimiento")
    temas = ", ".join(signo["temas"])
    
    prompt = f"""Eres un tarotista experto. Escribí una lectura para {signo['nombre']} con la carta "{card}".
Significado: {significado_carta}.
AUDIENCIA: 45-64 años, LATAM. Tono directo.
Mencioná: {temas}.
Máximo 70 palabras. NO uses clichés. Solo la lectura pura.

JSON:
{{"title": "{signo['nombre'].upper()} HOY | {card}", "lectura": "texto aquí", "description": "Tarot de hoy para {signo['nombre']}."}}"""

    data = None
    for _ in range(3):
        try:
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}], temperature=0.9, max_tokens=350,
            )
            raw = resp.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
            parsed = json.loads(raw)
            if len(parsed.get("lectura", "").split()) >= 30:
                data = parsed
                break
        except: time.sleep(2)

    if not data:
        data = {"title": f"{signo['nombre'].upper()} HOY | {card}", "lectura": f"{signo['nombre']}, {card} llega para mostrarte el camino.", "description": "Tarot"}

    data["script"] = f"{data['lectura']} {CTA_COMMENT} {CTA_SAVE} {CTA_HOOK} {CTA_FINAL}"
    data["tags"] = ["tarot", signo['nombre'].lower(), "tarot gratis", "horoscopo"]
    return data

def generate_voice(script: str, output_path: str, elemento: str = "Fuego") -> float:
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=script)
    voice_name = os.getenv("GOOGLE_TTS_VOICE", VOCES_POR_ELEMENTO.get(elemento, "es-US-Neural2-A"))
    voice = texttospeech.VoiceSelectionParams(language_code="es-US", name=voice_name, ssml_gender=texttospeech.SsmlVoiceGender.FEMALE)
    
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=0.95, volume_gain_db=1.0)
    response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    Path(output_path).write_bytes(response.audio_content)
    clip = AudioFileClip(output_path)
    duration = clip.duration
    clip.close()
    return duration

def download_pexels_video(card: str, output_path: str) -> bool:
    api_key = os.environ["PEXELS_API_KEY"]
    queries = CARD_PEXELS.get(card, DEFAULT_QUERIES)
    random.shuffle(queries)
    for q in queries[:2] + ["dark mystical purple"]:
        try:
            resp = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": api_key}, params={"query": q, "per_page": 10, "size": "medium"}, timeout=30)
            videos = resp.json().get("videos", [])
            if videos:
                video = random.choice(videos)
                chosen = sorted(video.get("video_files", []), key=lambda f: f.get("width", 0))[-1]
                with requests.get(chosen["link"], stream=True, timeout=90) as r:
                    with open(output_path, "wb") as out:
                        for chunk in r.iter_content(chunk_size=65536): out.write(chunk)
                return True
        except: continue
    return False

def _make_tarot_card_visual(card: str) -> np.ndarray:
    w, h = 400, 600
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        idx = ARCANOS.index(card)
        img_path = Path("cards") / f"m{idx:02d}.jpg"
        if img_path.exists():
            card_img = Image.open(img_path).convert("RGBA").resize((360, 560), Image.LANCZOS)
            img.paste(card_img, (20, 20))
            draw.rectangle([(0, 0), (w-1, h-1)], outline=C_GOLD, width=6)
            draw.rectangle([(10, 10), (w-11, h-11)], outline=C_GOLD_LIGHT, width=2)
            return np.array(img)
    except: pass

    # Fallback geométrico
    for y in range(h):
        t = y / h
        draw.line([(0, y), (w, y)], fill=(int(40*(1-t)), int(20*(1-t)), int(80*(1-t)), 240))
    draw.rectangle([(0, 0), (w-1, h-1)], outline=C_GOLD, width=6)
    draw.rectangle([(10, 10), (w-11, h-11)], outline=C_GOLD_LIGHT, width=2)
    cx, cy = w//2, h//2 - 40
    draw.ellipse([cx-90, cy-90, cx+90, cy+90], outline=C_GOLD_LIGHT, width=2)
    draw.polygon([(cx, cy-45), (cx+45, cy), (cx, cy+45), (cx-45, cy)], outline=C_GOLD_LIGHT, width=3)
    font_card = _fit_font_to_width(card.upper(), w - 40, 48, 24)
    bbox = draw.textbbox((0, 0), card.upper(), font=font_card)
    draw.text(((w-(bbox[2]-bbox[0]))//2, h-120), card.upper(), font=font_card, fill=C_TEXT)
    return np.array(img)

def _make_hook_overlay(signo: dict, card: str) -> np.ndarray:
    w, h = VIDEO_W, VIDEO_H
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Fondo semitransparente para el texto
    layout = random.choice(LAYOUT_STYLES)
    phrase = random.choice(HOOK_PHRASES)
    
    if layout == "TOP_TEXT":
        draw.rectangle([(0, 0), (w, h//3)], fill=(0,0,0,180))
        f1 = _fit_font_to_width(phrase, w-80, 70, 44)
        f2 = _fit_font_to_width(signo['nombre'].upper(), w-80, 60, 38)
        bbox1 = draw.textbbox((0,0), phrase, font=f1)
        draw.text(((w-(bbox1[2]-bbox1[0]))//2, 150), phrase, font=f1, fill=C_GOLD)
        bbox2 = draw.textbbox((0,0), signo['nombre'].upper(), font=f2)
        draw.text(((w-(bbox2[2]-bbox2[0]))//2, 250), signo['nombre'].upper(), font=f2, fill=C_TEXT)

    elif layout == "CENTER_BOX":
        draw.rectangle([(40, h//2 - 150), (w-40, h//2 + 150)], fill=(0,0,0,220), outline=C_GOLD, width=4)
        f1 = _fit_font_to_width(signo['nombre'].upper(), w-100, 60, 36)
        f2 = _fit_font_to_width(phrase, w-100, 50, 30)
        bbox1 = draw.textbbox((0,0), signo['nombre'].upper(), font=f1)
        draw.text(((w-(bbox1[2]-bbox1[0]))//2, h//2 - 90), signo['nombre'].upper(), font=f1, fill=C_GOLD)
        bbox2 = draw.textbbox((0,0), phrase, font=f2)
        draw.text(((w-(bbox2[2]-bbox2[0]))//2, h//2 + 10), phrase, font=f2, fill=C_TEXT)

    elif layout == "BOTTOM_TEXT":
        draw.rectangle([(0, h - h//3), (w, h)], fill=(0,0,0,200))
        f1 = _fit_font_to_width(phrase, w-80, 65, 40)
        f2 = _fit_font_to_width(f"Para {signo['nombre'].upper()}", w-80, 45, 30)
        bbox1 = draw.textbbox((0,0), phrase, font=f1)
        draw.text(((w-(bbox1[2]-bbox1[0]))//2, h - 250), phrase, font=f1, fill=C_RED_ALERT)
        bbox2 = draw.textbbox((0,0), f"Para {signo['nombre'].upper()}", font=f2)
        draw.text(((w-(bbox2[2]-bbox2[0]))//2, h - 140), f"Para {signo['nombre'].upper()}", font=f2, fill=C_TEXT)

    elif layout == "FULL_IMPACT":
        f1 = _fit_font_to_width(signo['nombre'].upper(), w-40, 90, 50)
        bbox1 = draw.textbbox((0,0), signo['nombre'].upper(), font=f1)
        draw.text(((w-(bbox1[2]-bbox1[0]))//2, 100), signo['nombre'].upper(), font=f1, fill=C_TEXT)
        draw.line([(100, 220), (w-100, 220)], fill=C_GOLD, width=4)
        f2 = _fit_font_to_width(phrase, w-40, 80, 45)
        bbox2 = draw.textbbox((0,0), phrase, font=f2)
        draw.text(((w-(bbox2[2]-bbox2[0]))//2, h-300), phrase, font=f2, fill=C_GOLD_LIGHT)

    else: # MINIMAL_CARD
        draw.rectangle([(40, 100), (w-40, 350)], fill=(0,0,0,230), outline=C_GOLD_LIGHT, width=2)
        f1 = _fit_font_to_width(phrase, w-100, 60, 36)
        f2 = _fit_font_to_width(signo['nombre'].upper(), w-100, 50, 30)
        bbox1 = draw.textbbox((0,0), phrase, font=f1)
        draw.text(((w-(bbox1[2]-bbox1[0]))//2, 160), phrase, font=f1, fill=C_TEXT)
        bbox2 = draw.textbbox((0,0), signo['nombre'].upper(), font=f2)
        draw.text(((w-(bbox2[2]-bbox2[0]))//2, 260), signo['nombre'].upper(), font=f2, fill=C_GOLD)

    return np.array(img)

# (El resto de las funciones de overlay, compose_video y generate se mantienen iguales a la v5.6,
# solo asegurate de que en compose_video el hook_clip use _make_hook_overlay(signo, card))