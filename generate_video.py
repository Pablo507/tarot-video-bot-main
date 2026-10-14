"""
generate_video.py
v4.0 — Adaptado a audiencia 45-64 años, Latinoamérica, hooks específicos.
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

# ─── Paletas de tinte ────────────────────────────────────────────────────────
PALETAS_TINT = [
    {"nombre": "purple", "color": (130, 43, 189), "opacity": 0.18},
    {"nombre": "blue",   "color": (15, 40, 100),  "opacity": 0.22},
    {"nombre": "wine",   "color": (90, 20, 60),   "opacity": 0.20},
    {"nombre": "teal",   "color": (15, 80, 80),   "opacity": 0.20},
    {"nombre": "indigo", "color": (50, 30, 120),  "opacity": 0.22},
]

# ─── Estructuras de guión ────────────────────────────────────────────────────
SCRIPT_STRUCTURES = [
    "PREGUNTA_DIRECTA",
    "ESCENA_SENSORIAL",
    "AFIRMACION_FUERTE",
    "NOMBRE_DIRECTO",
    "CONTRASTE",
]

# ─── NUEVO: CTAs específicos según objetivo ──────────────────────────────────
CTA_COMMENTS = [
    "Contame: ¿amor, trabajo o familia? Votá en comentarios.",
    "¿Te pasó algo así esta semana? Te leo abajo.",
    "¿En qué área de tu vida sentís esto? Contame 👇",
    "¿Estás pasando por esto? Escribime abajo.",
    "¿Qué te despertó esto? Contame en comentarios.",
]

CTA_SHARES = [
    "Etiquetá a alguien de {signo} que necesita leer esto hoy.",
    "Si tenés un amigo de {signo}, pasale este video.",
    "Mandáselo a ese {signo} que está pasando un momento difícil.",
    "Compartilo con quien lo necesite escuchar.",
    "Si te resonó, mandáselo a un {signo} que conozcas.",
]

CTA_HOOKS = [
    "Si querés una carta así cada mañana, te la mando por WhatsApp.",
    "Esto que sentís hoy, mañana puede ser distinto. Te aviso por WhatsApp.",
    "No dejes que la energía del día se te pase. Te la mando a tu WhatsApp.",
    "Tu carta de mañana ya está escrita. Te la cuento por WhatsApp.",
    "Cada mañana tengo algo nuevo para decirte. Te lo mando por WhatsApp.",
]

# ─── NUEVO: Hooks visuales adaptados a audiencia 45+ ─────────────────────────
# Estructura: (emoji/etiqueta grande, texto secundario)
HOOK_STYLES = [
    "PREGUNTA_SIGNO",      # GÉMINIS, ¿ESTÁS LISTO?
    "AFIRMACION_URGENTE",  # GÉMINIS, ESCUCHAME
    "PREGUNTA_CARTA",      # ¿QUÉ TE ESPERA HOY?
    "NOMBRE_CARTA",        # GÉMINIS + LA FUERZA
    "CONTEO",              # EL ARCANO DEL DÍA
]

# ─── Offsets únicos por signo ────────────────────────────────────────────────
SIGN_CARD_OFFSETS = [0, 7, 14, 3, 10, 17, 4, 11, 18, 5, 12, 19]

SIGNOS = [
    {"nombre": "Aries", "emoji": "♈", "fechas": "21 mar – 19 abr", "elemento": "Fuego", "planeta": "Marte",
     "tono": "impulsivo, valiente, directo",
     "temas": ["acción inmediata", "liderazgo", "coraje para empezar algo nuevo", "paciencia con los demás"]},
    {"nombre": "Tauro", "emoji": "♉", "fechas": "20 abr – 20 may", "elemento": "Tierra", "planeta": "Venus",
     "tono": "sensual, estable, terco",
     "temas": ["seguridad material", "placeres simples", "constancia", "soltar lo que ya no nutre"]},
    {"nombre": "Géminis", "emoji": "♊", "fechas": "21 may – 20 jun", "elemento": "Aire", "planeta": "Mercurio",
     "tono": "curioso, comunicativo, disperso",
     "temas": ["comunicación", "aprendizaje", "decisiones con la mente clara", "elegir una sola cosa"]},
    {"nombre": "Cáncer", "emoji": "♋", "fechas": "21 jun – 22 jul", "elemento": "Agua", "planeta": "Luna",
     "tono": "emocional, protector, nostálgico",
     "temas": ["familia", "hogar", "sanar heridas del pasado", "poner límites emocionales"]},
    {"nombre": "Leo", "emoji": "♌", "fechas": "23 jul – 22 ago", "elemento": "Fuego", "planeta": "Sol",
     "tono": "dramático, generoso, orgulloso",
     "temas": ["brillar sin culpa", "creatividad", "reconocimiento", "humildad"]},
    {"nombre": "Virgo", "emoji": "♍", "fechas": "23 ago – 22 sep", "elemento": "Tierra", "planeta": "Mercurio",
     "tono": "analítico, perfeccionista, servicial",
     "temas": ["orden", "salud", "servicio a otros", "soltar el perfeccionismo"]},
    {"nombre": "Libra", "emoji": "♎", "fechas": "23 sep – 22 oct", "elemento": "Aire", "planeta": "Venus",
     "tono": "diplomático, estético, indeciso",
     "temas": ["relaciones", "belleza", "equilibrio", "decidir sin miedo al conflicto"]},
    {"nombre": "Escorpio", "emoji": "♏", "fechas": "23 oct – 21 nov", "elemento": "Agua", "planeta": "Plutón",
     "tono": "intenso, transformador, reservado",
     "temas": ["transformación profunda", "poder personal", "sanar celos", "confiar de nuevo"]},
    {"nombre": "Sagitario", "emoji": "♐", "fechas": "22 nov – 21 dic", "elemento": "Fuego", "planeta": "Júpiter",
     "tono": "aventurero, filosófico, exagerado",
     "temas": ["expansión", "viajes", "fe en el futuro", "compromiso concreto"]},
    {"nombre": "Capricornio", "emoji": "♑", "fechas": "22 dic – 19 ene", "elemento": "Tierra", "planeta": "Saturno",
     "tono": "disciplinado, ambicioso, frío",
     "temas": ["metas a largo plazo", "responsabilidad", "trabajo", "permitirse disfrutar"]},
    {"nombre": "Acuario", "emoji": "♒", "fechas": "20 ene – 18 feb", "elemento": "Aire", "planeta": "Urano",
     "tono": "rebelde, original, distante",
     "temas": ["libertad", "innovación", "amistades", "conectar con las emociones"]},
    {"nombre": "Piscis", "emoji": "♓", "fechas": "19 feb – 20 mar", "elemento": "Agua", "planeta": "Neptuno",
     "tono": "soñador, compasivo, evasivo",
     "temas": ["intuición", "arte", "espiritualidad", "poner límites y aterrizar sueños"]},
]

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
    "El Loco":               ["adventure path nature", "freedom road", "leap cliff", "sunrise hiking trail", "wanderlust mountains"],
    "El Mago":               ["mystical candle purple", "magic ritual dark", "crystal ball", "alchemy tools", "incense smoke"],
    "La Sacerdotisa":        ["moon night purple", "mystery veil", "moonlight dark", "fog forest night", "veiled woman silhouette"],
    "La Emperatriz":         ["nature green abundance", "flowers garden", "earth goddess", "golden wheat field", "fertile garden"],
    "El Emperador":          ["mountain peak", "stone throne", "power dark sky", "rocky cliff sunset", "throne ancient"],
    "El Hierofante":         ["ancient temple", "spiritual ceremony", "sacred candle", "church candles", "monk silhouette"],
    "Los Enamorados":        ["couple sunset", "heart light bokeh", "love romance", "holding hands sunset", "two silhouettes"],
    "El Carro":              ["road ahead night", "speed motion blur", "triumph victory", "highway headlights", "night drive"],
    "La Fuerza":             ["lion majestic", "strength nature", "powerful animal", "lion portrait", "mountain strength"],
    "La Ermitaño":           ["lantern night dark", "solitude path fog", "mystical forest", "old man lantern", "cave light"],
    "La Rueda de la Fortuna":["spinning stars galaxy", "cosmic wheel", "universe rotation", "galaxy spin", "clock mechanism"],
    "La Justicia":           ["scales balance", "law justice", "symmetry architecture", "marble statue blindfold", "sword light"],
    "La Colgado":            ["water reflection", "hanging tree", "peaceful surrender", "man hanging rope", "still lake"],
    "La Muerte":             ["autumn leaves falling", "transformation dark", "rebirth nature", "skeleton skull art", "withered rose"],
    "La Templanza":          ["water pour light", "balance zen", "flowing river", "angel pouring water", "two cups"],
    "El Diablo":             ["fire dark flames", "smoke dramatic", "red dark abstract", "red smoke dark", "horned shadow"],
    "La Torre":              ["lightning storm dramatic", "tower dark", "storm clouds", "tower ruins", "lightning strike"],
    "La Estrella":           ["night sky stars", "galaxy milky way", "star field purple", "blue starry sky", "constellation"],
    "La Luna":               ["full moon night", "moon reflection water", "lunar mystical", "wolf howling moon", "crescent moon dark"],
    "El Sol":                ["sunrise golden", "sunlight rays", "bright sun nature", "sunflower closeup", "golden hour sky"],
    "La Juicio":             ["sunrise dramatic", "awakening light", "epic sky clouds", "clouds parted light", "trumpet sky"],
    "La Mundo":              ["earth globe space", "world complete", "universe harmony", "planet space art", "flowers circle"],
}

DEFAULT_QUERIES = ["mystical dark purple", "night sky stars", "smoke dark background", "purple abstract", "moon clouds"]

VOCES_POR_ELEMENTO = {
    "Fuego":  "es-US-Neural2-A",
    "Tierra": "es-US-Neural2-A",
    "Aire":   "es-US-Journey-F",
    "Agua":   "es-US-Neural2-A",
}
VOCES_SIN_PITCH = {"es-US-Journey-F", "es-US-Journey-D", "es-US-Journey-O"}

_BOLD_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "C:/Windows/Fonts/georgiab.ttf",
    "C:/Windows/Fonts/timesbd.ttf",
]


def get_card_for_sign(signo_idx: int) -> str:
    hoy = datetime.now()
    day_offset = (hoy.year * 31 + hoy.month * 17 + hoy.day) % len(ARCANOS)
    idx = (day_offset + SIGN_CARD_OFFSETS[signo_idx]) % len(ARCANOS)
    return ARCANOS[idx]


def _load_fonts(size_large, size_medium, size_small):
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
        try_load(_BOLD_FONT_PATHS, size_large),
        try_load(_BOLD_FONT_PATHS, size_medium),
        try_load(reg_candidates, size_small),
    )


def _fit_font_to_width(text: str, max_width: int, initial_size: int, min_size: int = 36):
    size = initial_size
    while size > min_size:
        font = None
        for p in _BOLD_FONT_PATHS:
            try:
                font = ImageFont.truetype(p, size)
                break
            except Exception:
                continue
        if font is None:
            return ImageFont.load_default()
        bbox = font.getbbox(text)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            return font
        size -= 2
    for p in _BOLD_FONT_PATHS:
        try:
            return ImageFont.truetype(p, min_size)
        except Exception:
            continue
    return ImageFont.load_default()


def _is_too_similar(new_script: str, prev_scripts: list, umbral: float = 0.55) -> bool:
    new_set = set(w.lower().strip(".,!?¡¿;:") for w in new_script.split() if len(w) > 4)
    if not new_set:
        return False
    for prev in prev_scripts:
        prev_set = set(w.lower().strip(".,!?¡¿;:") for w in prev.split() if len(w) > 4)
        if not prev_set:
            continue
        overlap = len(new_set & prev_set) / len(new_set | prev_set)
        if overlap > umbral:
            return True
    return False


def generate_reading(signo: dict, card: str) -> dict:
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    hoy = datetime.now().strftime("%d de %B de %Y")

    temas = ", ".join(signo["temas"])
    seed = random.randint(1, 99999)
    structure = random.choice(SCRIPT_STRUCTURES)
    cta_comment = random.choice(CTA_COMMENTS)
    cta_share = random.choice(CTA_SHARES).format(signo=signo['nombre'])
    cta_hook = random.choice(CTA_HOOKS)

    prompt = f"""Eres un tarotista con 20 años de experiencia, conocido por ser directo y honesto. NO sos un generador de plantillas genéricas.

Escribí un guión ORIGINAL para un TikTok de tarot para el signo {signo['nombre']} ({signo['elemento']}, regido por {signo['planeta']}) con la carta "{card}".

AUDIENCIA OBJETIVO: adultos de 45 a 64 años, principalmente de Latinoamérica (Venezuela, Argentina, Uruguay, México). Hablan español neutro. Son personas con experiencia de vida, que valoran la sabiduría práctica, no la fantasía new age. NO les hables como si tuvieran 20 años.

ESTRUCTURA OBLIGATORIA: **{structure}**

- PREGUNTA_DIRECTA: arrancá con una pregunta existencial fuerte (ej: "¿Cuánto tiempo vas a seguir esperando?"). NO menciones el signo en la primera frase.
- ESCENA_SENSORIAL: arrancá con una imagen concreta y física (ej: "Hay algo que se está rompiendo por dentro, como una rama que no aguanta más peso").
- AFIRMACION_FUERTE: arrancá con algo controversial o brutalmente honesto (ej: "Estás agotado y lo disimulás muy bien").
- NOMBRE_DIRECTO: llamá al signo por su nombre de forma íntima (ej: "Aries, pará un segundo").
- CONTRASTE: contrastá al signo con los demás (ej: "Mientras todos avanzan, vos estás en pausa").

REGLAS OBLIGATORIAS:
1. Tono: {signo['tono']}. Hablale a UN {signo['nombre']} específico, como si estuvieras sentado al lado suyo tomando un café.
2. Mencioná AL MENOS DOS de estos temas: {temas}.
3. PROHIBIDO usar estas frases: "el universo te pide", "es momento de fluir", "confía en el proceso", "todo sucede por una razón", "estás en un viaje", "es momento de soltar", "abrí tu corazón".
4. Incluí UNA metáfora sensorial concreta y distinta (nada de "flores", "ríos" o "mariposas").
5. Máximo 110 palabras, mínimo 90.
6. La PRIMERA FRASE debe ser un gancho de máximo 10 palabras que atrape en 2 segundos. Que sea específica y provoque curiosidad.
7. Después del desarrollo incluí esta frase EXACTA para invitar a comentar: "{cta_comment}"
8. Luego incluí esta frase EXACTA para invitar a compartir: "{cta_share}"
9. Después incluí esta transición: "{cta_hook}"
10. Terminá EXACTAMENTE con: "Para recibir tu carta del tarot cada mañana en tu WhatsApp, suscribite en tarotgratis punto online por menos de cinco dólares al mes"

Variación semilla (ignorala en el texto): {seed}

Devolvé SOLO un JSON válido sin markdown:
{{
  "title": "{signo['nombre'].upper()} HOY | {card} | Tarot {hoy}",
  "script": "tu guión aquí",
  "description": "🔮 Tarot de hoy para {signo['nombre']} con {card}. Recibí tu carta diaria en WhatsApp 👇",
  "tags": ["tarot", "{signo['nombre'].lower()}", "tarot diario", "carta del día", "tarot gratis", "tarotonline", "{signo['elemento'].lower()}"]
}}"""

    resp = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=1.15,
        top_p=0.95,
        max_tokens=750,
    )
    raw = resp.choices[0].message.content.strip()
    print("Respuesta cruda de Groq:", raw[:200])

    clean_raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        data = json.loads(clean_raw)
    except json.JSONDecodeError:
        tema1, tema2 = random.sample(signo["temas"], 2)
        fallback_text = (
            f"{signo['nombre']}, dejá lo que estás haciendo un segundo. "
            f"{card} tiene algo urgente para decirte hoy. "
            f"Como {signo['elemento'].lower()} que sos, algo se está moviendo por dentro. "
            f"El arcano te habla de {tema1} y de {tema2}. "
            f"No es momento de quedarte quieto. "
            f"{cta_comment} "
            f"{cta_share} "
            f"{cta_hook} "
            "Para recibir tu carta del tarot cada mañana en tu WhatsApp, suscribite en tarotgratis punto online por menos de cinco dólares al mes"
        )
        data = {
            "title": f"{signo['nombre'].upper()} HOY | {card} | Tarot {hoy}",
            "script": fallback_text,
            "description": f"Tarot diario para {signo['nombre']} con {card} 🔮",
            "tags": ["tarot", signo['nombre'].lower(), "tarot diario", signo['elemento'].lower()],
        }

    palabras = len(data.get("script", "").split())
    if palabras < 95 or palabras > 160:
        print(f"   ⚠️  Guión con {palabras} palabras fuera de rango, regenerando...")
        return generate_reading(signo, card)

    return data


def generate_voice(script: str, output_path: str, elemento: str = "Fuego") -> float:
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=script)

    voice_name = os.getenv(
        "GOOGLE_TTS_VOICE",
        VOCES_POR_ELEMENTO.get(elemento, "es-US-Neural2-A"),
    )

    voice = texttospeech.VoiceSelectionParams(
        language_code="es-US",
        name=voice_name,
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
    )

    if voice_name in VOCES_SIN_PITCH:
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=0.92,
            volume_gain_db=1.0,
        )
    else:
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=0.92,
            pitch=-1.0,
            volume_gain_db=1.0,
        )

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config,
    )
    Path(output_path).write_bytes(response.audio_content)
    clip = AudioFileClip(output_path)
    duration = clip.duration
    clip.close()
    print(f"Duración exacta del audio TTS: {duration} segundos")
    return duration


def download_pexels_video(card: str, output_path: str) -> bool:
    api_key = os.environ["PEXELS_API_KEY"]
    queries = CARD_PEXELS.get(card, DEFAULT_QUERIES)
    random.shuffle(queries)
    fallbacks = ["dark mystical purple", "night sky stars", "purple abstract background"]
    attempt_queries = queries[:2] + fallbacks

    videos = []
    for attempt_query in attempt_queries:
        print(f"   Pexels: '{attempt_query}'...")
        try:
            resp = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": api_key},
                params={"query": attempt_query, "per_page": 15, "size": "medium"},
                timeout=30,
            )
            resp.raise_for_status()
            videos = resp.json().get("videos", [])
            if videos:
                break
        except Exception as e:
            print(f"   ⚠️  Error Pexels: {e}")
            continue

    if not videos:
        return False

    video  = random.choice(videos[:12])
    files  = sorted(video.get("video_files", []), key=lambda f: f.get("width", 0))
    chosen = next((f for f in reversed(files) if f.get("width", 9999) <= 1920), files[-1])

    with requests.get(chosen["link"], stream=True, timeout=90) as r:
        r.raise_for_status()
        with open(output_path, "wb") as out:
            for chunk in r.iter_content(chunk_size=65536):
                out.write(chunk)
    return True


# ═══════════════════════════════════════════════════════════════════════════
# HOOKS VISUALES adaptados a audiencia 45+ (más directos, menos juego visual)
# ═══════════════════════════════════════════════════════════════════════════

def _hook_bg_gradient(w, h, color_top, color_bottom, alpha_max=230):
    bg = Image.new("RGBA", (w, h))
    for y in range(h):
        t = y / h
        r = int(color_top[0] * (1 - t) + color_bottom[0] * t)
        g = int(color_top[1] * (1 - t) + color_bottom[1] * t)
        b = int(color_top[2] * (1 - t) + color_bottom[2] * t)
        for x in range(w):
            bg.putpixel((x, y), (r, g, b, alpha_max))
    return bg


def _gold_decorative_line(draw, w, y, start=140, end_offset=140):
    for xi in range(start, w - end_offset):
        t = (xi - start) / (w - start - end_offset)
        intensity = 1 - abs(t * 2 - 1)
        ga = int(220 * intensity)
        draw.point((xi, y), fill=(*C_GOLD, ga))


def _draw_arrows(draw, w, y_start, count=3):
    cx = w // 2
    for i in range(count):
        y0 = y_start + i * 25
        alpha = 200 - i * 40
        draw.polygon(
            [(cx - 30, y0), (cx + 30, y0), (cx, y0 + 22)],
            fill=(*C_GOLD, alpha),
        )


def _make_hook_overlay(signo: dict, card: str) -> np.ndarray:
    w, h = VIDEO_W, VIDEO_H
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bg = _hook_bg_gradient(w, h, C_BG_DEEP, C_BG_MID)
    img = Image.alpha_composite(img, bg)
    draw = ImageDraw.Draw(img)

    style = random.choice(HOOK_STYLES)
    print(f"   🎨 Hook style: {style}")

    if style == "PREGUNTA_SIGNO":
        _gold_decorative_line(draw, w, 340)
        line1 = signo['nombre'].upper() + ","
        font_line1 = _fit_font_to_width(line1, w - 80, 68, 40)
        bbox = draw.textbbox((0, 0), line1, font=font_line1)
        x = (w - (bbox[2] - bbox[0])) // 2
        draw.text((x + 4, 424), line1, font=font_line1, fill=(0, 0, 0, 240))
        draw.text((x, 420), line1, font=font_line1, fill=(*C_GOLD_LIGHT, 255))

        line2 = "¿ESTÁS LISTO?"
        font_line2 = _fit_font_to_width(line2, w - 80, 58, 36)
        bbox = draw.textbbox((0, 0), line2, font=font_line2)
        x = (w - (bbox[2] - bbox[0])) // 2
        draw.text((x + 3, 524), line2, font=font_line2, fill=(0, 0, 0, 230))
        draw.text((x, 520), line2, font=font_line2, fill=(*C_TEXT, 250))

        _gold_decorative_line(draw, w, 620, start=180, end_offset=180)
        sub_text = f"Hoy sale {card} para vos"
        font_sub = _fit_font_to_width(sub_text, w - 80, 38, 24)
        bbox = draw.textbbox((0, 0), sub_text, font=font_sub)
        sx = (w - (bbox[2] - bbox[0])) // 2
        draw.text((sx, 660), sub_text, font=font_sub, fill=(*C_MUTED, 245))

    elif style == "AFIRMACION_URGENTE":
        _gold_decorative_line(draw, w, 320)
        line1 = signo['nombre'].upper() + ","
        font_line1 = _fit_font_to_width(line1, w - 80, 68, 40)
        bbox = draw.textbbox((0, 0), line1, font=font_line1)
        x = (w - (bbox[2] - bbox[0])) // 2
        draw.text((x + 4, 424), line1, font=font_line1, fill=(0, 0, 0, 240))
        draw.text((x, 420), line1, font=font_line1, fill=(*C_GOLD_LIGHT, 255))

        line2 = "ESCUCHAME"
        font_line2 = _fit_font_to_width(line2, w - 80, 58, 36)
        bbox = draw.textbbox((0, 0), line2, font=font_line2)
        x = (w - (bbox[2] - bbox[0])) // 2
        draw.text((x + 3, 524), line2, font=font_line2, fill=(0, 0, 0, 230))
        draw.text((x, 520), line2, font=font_line2, fill=(*C_TEXT, 250))

        _gold_decorative_line(draw, w, 620, start=180, end_offset=180)
        sub_text = f"{card} tiene algo para decirte"
        font_sub = _fit_font_to_width(sub_text, w - 80, 34, 22)
        bbox = draw.textbbox((0, 0), sub_text, font=font_sub)
        sx = (w - (bbox[2] - bbox[0])) // 2
        draw.text((sx, 660), sub_text, font=font_sub, fill=(*C_MUTED, 245))

    elif style == "PREGUNTA_CARTA":
        _gold_decorative_line(draw, w, 320)
        line1 = "¿QUÉ TE ESPERA"
        font_line1 = _fit_font_to_width(line1, w - 80, 60, 38)
        bbox = draw.textbbox((0, 0), line1, font=font_line1)
        x = (w - (bbox[2] - bbox[0])) // 2
        draw.text((x + 4, 424), line1, font=font_line1, fill=(0, 0, 0, 240))
        draw.text((x, 420), line1, font=font_line1, fill=(*C_GOLD_LIGHT, 255))

        line2 = "HOY?"
        font_line2 = _fit_font_to_width(line2, w - 80, 60, 38)
        bbox = draw.textbbox((0, 0), line2, font=font_line2)
        x = (w - (bbox[2] - bbox[0])) // 2
        draw.text((x + 4, 524), line2, font=font_line2, fill=(0, 0, 0, 240))
        draw.text((x, 520), line2, font=font_line2, fill=(*C_GOLD_LIGHT, 255))

        _gold_decorative_line(draw, w, 620, start=180, end_offset=180)
        sub_text = f"Tu carta: {card}"
        font_sub = _fit_font_to_width(sub_text, w - 80, 42, 26)
        bbox = draw.textbbox((0, 0), sub_text, font=font_sub)
        sx = (w - (bbox[2] - bbox[0])) // 2
        draw.text((sx + 2, 660), sub_text, font=font_sub, fill=(0, 0, 0, 230))
        draw.text((sx, 658), sub_text, font=font_sub, fill=(*C_TEXT, 250))

    elif style == "NOMBRE_CARTA":
        line1 = signo['nombre'].upper()
        font_line1 = _fit_font_to_width(line1, w - 80, 68, 40)
        bbox = draw.textbbox((0, 0), line1, font=font_line1)
        x = (w - (bbox[2] - bbox[0])) // 2
        draw.text((x + 4, 400), line1, font=font_line1, fill=(0, 0, 0, 240))
        draw.text((x, 396), line1, font=font_line1, fill=(*C_TEXT, 250))

        glyph = CARD_GLYPHS.get(card, "✨")
        font_glyph = None
        for p in _BOLD_FONT_PATHS:
            try:
                font_glyph = ImageFont.truetype(p, 90)
                break
            except Exception:
                continue
        if font_glyph is None:
            font_glyph = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), glyph, font=font_glyph)
        gx = (w - (bbox[2] - bbox[0])) // 2
        draw.text((gx, 500), glyph, font=font_glyph, fill=(*C_GOLD, 255))

        _gold_decorative_line(draw, w, 640, start=180, end_offset=180)

        line2 = card.upper()
        font_line2 = _fit_font_to_width(line2, w - 80, 54, 32)
        bbox = draw.textbbox((0, 0), line2, font=font_line2)
        x = (w - (bbox[2] - bbox[0])) // 2
        draw.text((x + 3, 684), line2, font=font_line2, fill=(0, 0, 0, 230))
        draw.text((x, 680), line2, font=font_line2, fill=(*C_GOLD_LIGHT, 255))

    else:  # CONTEO
        _gold_decorative_line(draw, w, 340)
        line1 = "EL ARCANO"
        font_line1 = _fit_font_to_width(line1, w - 80, 56, 36)
        bbox = draw.textbbox((0, 0), line1, font=font_line1)
        x = (w - (bbox[2] - bbox[0])) // 2
        draw.text((x + 3, 444), line1, font=font_line1, fill=(0, 0, 0, 220))
        draw.text((x, 440), line1, font=font_line1, fill=(*C_MUTED, 245))

        line2 = "DEL DÍA"
        font_line2 = _fit_font_to_width(line2, w - 80, 56, 36)
        bbox = draw.textbbox((0, 0), line2, font=font_line2)
        x = (w - (bbox[2] - bbox[0])) // 2
        draw.text((x + 3, 514), line2, font=font_line2, fill=(0, 0, 0, 220))
        draw.text((x, 510), line2, font=font_line2, fill=(*C_MUTED, 245))

        _gold_decorative_line(draw, w, 590, start=180, end_offset=180)

        card_upper = card.upper()
        font_card = _fit_font_to_width(card_upper, w - 80, 62, 36)
        bbox = draw.textbbox((0, 0), card_upper, font=font_card)
        x = (w - (bbox[2] - bbox[0])) // 2
        draw.text((x + 4, 634), card_upper, font=font_card, fill=(0, 0, 0, 240))
        draw.text((x, 630), card_upper, font=font_card, fill=(*C_GOLD_LIGHT, 255))

        sub_text = f"Para {signo['nombre']}"
        font_sub = _fit_font_to_width(sub_text, w - 80, 36, 24)
        bbox = draw.textbbox((0, 0), sub_text, font=font_sub)
        sx = (w - (bbox[2] - bbox[0])) // 2
        draw.text((sx, 730), sub_text, font=font_sub, fill=(*C_TEXT, 235))

    font_small = None
    for p in _BOLD_FONT_PATHS:
        try:
            font_small = ImageFont.truetype(p, 30)
            break
        except Exception:
            continue
    if font_small is None:
        font_small = ImageFont.load_default()

    hint_text = "Mirá hasta el final"
    bbox = draw.textbbox((0, 0), hint_text, font=font_small)
    hx2 = (w - (bbox[2] - bbox[0])) // 2
    draw.text((hx2, 800), hint_text, font=font_small, fill=(*C_MUTED, 240))

    _draw_arrows(draw, w, 850)

    return np.array(img)


def _make_title_overlay(signo: dict, card: str) -> np.ndarray:
    w, h = VIDEO_W, 390
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bg  = Image.new("RGBA", (w, h))
    for y in range(h):
        alpha = int(210 * max(0, 1 - (y / h) * 1.0))
        for x in range(w):
            bg.putpixel((x, y), (*C_BG_DEEP, alpha))
    img  = Image.alpha_composite(img, bg)
    draw = ImageDraw.Draw(img)

    font_sign, font_card, font_url = _load_fonts(50, 32, 42)
    GOLD_A  = (*C_GOLD, 255)
    WHITE_A = (*C_TEXT, 240)
    MUTED_A = (*C_MUTED, 230)

    margin = 40
    draw.line([(margin, 16), (w - margin, 16)], fill=GOLD_A, width=2)

    signo_text = f"-- {signo['nombre'].upper()} --"
    bbox = draw.textbbox((0, 0), signo_text, font=font_sign)
    x = (w - (bbox[2]-bbox[0])) // 2
    draw.text((x+2, 28), signo_text, font=font_sign, fill=(0, 0, 0, 200))
    draw.text((x, 26), signo_text, font=font_sign, fill=GOLD_A)

    card_text = card.upper()
    bbox = draw.textbbox((0, 0), card_text, font=font_card)
    x = (w - (bbox[2]-bbox[0])) // 2
    draw.text((x+2, 92), card_text, font=font_card, fill=(0, 0, 0, 200))
    draw.text((x, 90), card_text, font=font_card, fill=WHITE_A)

    for xi in range(margin + 80, w - margin - 80):
        draw.point((xi, 138), fill=(*C_GOLD, 140))

    url_label = "Lectura gratis en:"
    font_sm = _load_fonts(24, 24, 22)[2]
    bbox = draw.textbbox((0, 0), url_label, font=font_sm)
    draw.text(((w - (bbox[2]-bbox[0])) // 2, 150), url_label, font=font_sm, fill=MUTED_A)

    url_text = "tarotgratis.online"
    bbox = draw.textbbox((0, 0), url_text, font=font_url)
    x = (w - (bbox[2]-bbox[0])) // 2
    draw.text((x+3, 183), url_text, font=font_url, fill=(0, 0, 0, 240))
    draw.text((x, 180), url_text, font=font_url, fill=GOLD_A)

    for xi in range(margin, w - margin):
        t = (xi - margin) / (w - 2*margin)
        intensity = 1 - abs(t*2-1)
        ga = int(210 * intensity)
        draw.point((xi, 246), fill=(*C_GOLD, ga))
    draw.point((w//2, 246), fill=(*C_GOLD_LIGHT, 255))

    return np.array(img)


def _make_cta_overlay() -> np.ndarray:
    w, h = VIDEO_W, 240
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bg = Image.new("RGBA", (w, h))
    for y in range(h):
        alpha = int(220 * (y / h))
        for x in range(w):
            bg.putpixel((x, y), (
                int(C_BG_DEEP[0] * .6),
                int(C_BG_DEEP[1] * .6),
                int(C_BG_MID[2] * .8),
                alpha,
            ))
    img = Image.alpha_composite(img, bg)
    draw = ImageDraw.Draw(img)

    font_big, font_med, font_sm = _load_fonts(44, 30, 22)
    GOLD_A  = (*C_GOLD, 255)
    WHITE_A = (*C_TEXT, 240)
    GOLD_L  = (*C_GOLD_LIGHT, 255)

    for x in range(w):
        t = x / w
        r = int(C_GOLD[0] + (C_GOLD_LIGHT[0] - C_GOLD[0]) * (1 - abs(t * 2 - 1)))
        g = int(C_GOLD[1] + (C_GOLD_LIGHT[1] - C_GOLD[1]) * (1 - abs(t * 2 - 1)))
        b = int(C_GOLD[2] + (C_GOLD_LIGHT[2] - C_GOLD[2]) * (1 - abs(t * 2 - 1)))
        draw.point((x, 12), fill=(r, g, b, 160))

    line1 = "📲 Tu carta del día en WhatsApp"
    bbox = draw.textbbox((0, 0), line1, font=font_sm)
    draw.text(((w - (bbox[2] - bbox[0])) // 2, 25), line1, font=font_sm, fill=WHITE_A)

    line2 = "tarotgratis.online"
    bbox = draw.textbbox((0, 0), line2, font=font_big)
    x = (w - (bbox[2] - bbox[0])) // 2
    draw.text((x + 3, 78), line2, font=font_big, fill=(0, 0, 0, 230))
    draw.text((x, 75), line2, font=font_big, fill=GOLD_A)

    line3 = "Solo $4.99/mes · Cancelá cuando quieras"
    bbox = draw.textbbox((0, 0), line3, font=font_sm)
    draw.text(((w - (bbox[2] - bbox[0])) // 2, 138), line3, font=font_sm, fill=WHITE_A)

    line4 = "👇 Suscribite en la web"
    bbox = draw.textbbox((0, 0), line4, font=font_med)
    draw.text(((w - (bbox[2] - bbox[0])) // 2, 175), line4, font=font_med, fill=GOLD_L)

    return np.array(img)


def _make_mid_cta_overlay() -> np.ndarray:
    w, h = VIDEO_W, 180
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    bg = Image.new("RGBA", (w, h))
    for y in range(h):
        alpha = min(215, 175 + int(40 * (y / h)))
        for x in range(w):
            bg.putpixel((x, y), (*C_BG_DEEP, alpha))
    img = Image.alpha_composite(img, bg)
    draw = ImageDraw.Draw(img)

    font_big, font_med, font_sm = _load_fonts(50, 32, 24)
    GOLD_A  = (*C_GOLD, 255)
    WHITE_A = (*C_TEXT, 245)

    for x in range(w):
        t = x / w
        r = int(C_GOLD[0] + (C_GOLD_LIGHT[0] - C_GOLD[0]) * (1 - abs(t * 2 - 1)))
        g = int(C_GOLD[1] + (C_GOLD_LIGHT[1] - C_GOLD[1]) * (1 - abs(t * 2 - 1)))
        b = int(C_GOLD[2] + (C_GOLD_LIGHT[2] - C_GOLD[2]) * (1 - abs(t * 2 - 1)))
        draw.point((x, 2), fill=(r, g, b, 220))
        draw.point((x, h - 3), fill=(r, g, b, 220))

    l1 = "🌙 Tu carta diaria por WhatsApp:"
    bbox = draw.textbbox((0, 0), l1, font=font_sm)
    draw.text(((w - (bbox[2] - bbox[0])) // 2, 22), l1, font=font_sm, fill=WHITE_A)

    l2 = "tarotgratis.online"
    bbox = draw.textbbox((0, 0), l2, font=font_big)
    x = (w - (bbox[2] - bbox[0])) // 2
    draw.text((x + 3, 68), l2, font=font_big, fill=(0, 0, 0, 240))
    draw.text((x, 65), l2, font=font_big, fill=GOLD_A)

    return np.array(img)


def _make_free_overlay() -> np.ndarray:
    w, h = VIDEO_W, 180
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bg = Image.new("RGBA", (w, h))
    for y in range(h):
        alpha = int(220 * (y / h))
        for x in range(w):
            bg.putpixel((x, y), (*C_BG_DEEP, alpha))
    img = Image.alpha_composite(img, bg)
    draw = ImageDraw.Draw(img)
    font_big, font_med, font_sm = _load_fonts(40, 28, 20)
    line1 = "📲 Descarga tu carta gratis en:"
    bbox = draw.textbbox((0, 0), line1, font=font_sm)
    draw.text(((w-(bbox[2]-bbox[0]))//2, 20), line1, font=font_sm, fill=(*C_TEXT,240))
    url = "tarotgratis.online"
    bbox = draw.textbbox((0, 0), url, font=font_big)
    x = (w-(bbox[2]-bbox[0]))//2
    draw.text((x+2, 70), url, font=font_big, fill=(0,0,0,240))
    draw.text((x, 68), url, font=font_big, fill=(*C_GOLD,255))
    return np.array(img)


def _make_pricing_overlay() -> np.ndarray:
    w, h = VIDEO_W, 280
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bg = Image.new("RGBA", (w, h))
    for y in range(h):
        alpha = int(220 * (y / h))
        for x in range(w):
            bg.putpixel((x, y), (*C_BG_DEEP, alpha))
    img = Image.alpha_composite(img, bg)
    draw = ImageDraw.Draw(img)
    font_big, font_med, font_sm = _load_fonts(52, 34, 24)
    precio = "$4.99 USD / mes"
    bbox = draw.textbbox((0, 0), precio, font=font_big)
    x = (w-(bbox[2]-bbox[0]))//2
    draw.text((x+2, 20), precio, font=font_big, fill=(0,0,0,240))
    draw.text((x, 18), precio, font=font_big, fill=(*C_GOLD,255))
    beneficios = [
        "📲 Carta del día en tu WhatsApp",
        "🔮 Interpretación personalizada por IA",
        "🔄 Cancela cuando quieras"
    ]
    for i, texto in enumerate(beneficios):
        y = 90 + i * 35
        draw.text((40, y), texto, font=font_sm, fill=(*C_TEXT,240))
    cta = "tarotgratis.online"
    bbox = draw.textbbox((0, 0), cta, font=font_big)
    x = (w-(bbox[2]-bbox[0]))//2
    draw.text((x+2, 210), cta, font=font_big, fill=(0,0,0,240))
    draw.text((x, 208), cta, font=font_big, fill=(*C_GOLD,255))
    return np.array(img)


def compose_video(bg_video_path, audio_path, signo, card, output_path,
                  cta_type="none", paleta_tint=None):
    if paleta_tint is None:
        paleta_tint = random.choice(PALETAS_TINT)

    audio = AudioFileClip(audio_path)
    total_duration = audio.duration + 1.0

    bg = VideoFileClip(bg_video_path, audio=False)
    if bg.duration < total_duration:
        loops = int(total_duration / bg.duration) + 2
        bg = concatenate_videoclips([bg.copy() for _ in range(loops)])
    bg = bg.subclip(0, total_duration)

    bg_ratio = bg.w / bg.h
    target_ratio = VIDEO_W / VIDEO_H
    if bg_ratio > target_ratio:
        bg = bg.resize(height=VIDEO_H)
        bg = bg.crop(x_center=bg.w / 2, width=VIDEO_W)
    else:
        bg = bg.resize(width=VIDEO_W)
        bg = bg.crop(y_center=bg.h / 2, height=VIDEO_H)

    dark = (
        ColorClip(size=(VIDEO_W, VIDEO_H), color=list(C_BG_DEEP))
        .set_opacity(0.30)
        .set_duration(total_duration)
    )

    tint_clip = (
        ColorClip(size=(VIDEO_W, VIDEO_H), color=list(paleta_tint["color"]))
        .set_opacity(paleta_tint["opacity"])
        .set_duration(total_duration)
    )

    hook_clip = (
        ImageClip(_make_hook_overlay(signo, card))
        .set_start(0.0)
        .set_duration(2.0)
        .set_position(("center", 0))
        .crossfadeout(0.4)
    )

    title_clip = (
        ImageClip(_make_title_overlay(signo, card))
        .set_start(2.0)
        .set_duration(total_duration - 2.0)
        .set_position(("center", 60))
        .crossfadein(0.4)
    )

    mid_start = total_duration * 0.40
    mid_clip = (
        ImageClip(_make_mid_cta_overlay())
        .set_start(mid_start)
        .set_duration(6.0)
        .set_position(("center", int(VIDEO_H * 0.50)))
        .crossfadein(0.8)
        .crossfadeout(0.8)
    )

    cta_start = max(1.0, total_duration - 7)
    cta_clip = (
        ImageClip(_make_cta_overlay())
        .set_start(cta_start)
        .set_duration(total_duration - cta_start)
        .set_position(("center", int(VIDEO_H * 0.38)))
        .crossfadein(1.0)
    )

    final_clips = [bg, dark, tint_clip, hook_clip, title_clip, mid_clip, cta_clip]

    if cta_type == "paid":
        pricing_clip = (
            ImageClip(_make_pricing_overlay())
            .set_start(max(1.0, total_duration - 5.0))
            .set_duration(5.0)
            .set_position(("center", int(VIDEO_H * 0.30)))
            .crossfadein(0.8)
        )
        final_clips.append(pricing_clip)
    elif cta_type == "free":
        free_clip = (
            ImageClip(_make_free_overlay())
            .set_start(max(1.0, total_duration - 4.0))
            .set_duration(4.0)
            .set_position(("center", int(VIDEO_H * 0.42)))
            .crossfadein(0.8)
        )
        final_clips.append(free_clip)

    TEMP_DIR.mkdir(exist_ok=True)
    final = CompositeVideoClip(
        final_clips,
        size=(VIDEO_W, VIDEO_H),
    ).set_audio(audio)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    final.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=str(TEMP_DIR / f"tmp_{Path(output_path).stem}.m4a"),
        remove_temp=True,
        threads=2,
        preset="ultrafast",
        verbose=False,
        logger=None,
    )
    for clip in [audio, bg, final]:
        try:
            clip.close()
        except:
            pass

    return output_path


def generate(signo_idx: int, cta_type: str = "none", prev_scripts: list = None) -> dict:
    OUTPUT_DIR.mkdir(exist_ok=True)
    TEMP_DIR.mkdir(exist_ok=True)

    signo = SIGNOS[signo_idx]
    card  = get_card_for_sign(signo_idx)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug  = f"{signo['nombre'].lower()}_{stamp}"

    paleta = random.choice(PALETAS_TINT)

    print(f"\n{signo['emoji']}  {signo['nombre']} — {card} [paleta: {paleta['nombre']}]")
    print("─" * 48)

    print("📝  Generando guión...")
    reading = generate_reading(signo, card)

    if prev_scripts:
        intentos = 0
        while _is_too_similar(reading["script"], prev_scripts) and intentos < 1:
            print(f"   ⚠️  Guión similar, reintentando ({intentos+1}/1)...")
            time.sleep(6)
            reading = generate_reading(signo, card)
            intentos += 1

    print(f"    {reading['title']}")

    audio_path = str(TEMP_DIR / f"{slug}.mp3")
    print("🎙️   Generando voz...")
    duration = generate_voice(reading["script"], audio_path, signo["elemento"])
    print(f"    {duration:.1f}s")

    bg_path = str(TEMP_DIR / f"{slug}_bg.mp4")
    print("🎬  Descargando fondo Pexels...")
    if not download_pexels_video(card, bg_path):
        raise RuntimeError(f"No se pudo descargar fondo para {signo['nombre']}")

    output_path = str(OUTPUT_DIR / f"{slug}.mp4")
    print(f"🎞️   Componiendo video con CTA: {cta_type}")
    compose_video(bg_path, audio_path, signo, card, output_path, cta_type, paleta)

    print(f"✅  {signo['nombre']} listo: {output_path}")

    return {
        "video_path": output_path,
        "title":      reading["title"],
        "description":reading["description"],
        "tags":       reading["tags"],
        "script":     reading["script"],
        "signo":      signo["nombre"],
        "card":       card,
        "duration_s": duration,
        "cta_type":   cta_type,
        "paleta":     paleta["nombre"],
    }