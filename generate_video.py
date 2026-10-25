"""
generate_video.py
v5.2 — Contenido profundo (IA solo escribe la lectura), CTAs automáticos por código y Carta Visual.
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

HOOK_THEMES = [
    {"name": "MISTICO", "bg_top": C_BG_DEEP, "bg_bottom": C_BG_MID, "text_main": C_GOLD_LIGHT, "text_sub": C_TEXT, "text_accent": C_GOLD, "color_alert": C_RED_ALERT},
    {"name": "OSCURO", "bg_top": (10, 10, 15), "bg_bottom": (30, 30, 35), "text_main": (255, 255, 255), "text_sub": (200, 200, 200), "text_accent": (255, 50, 50), "color_alert": (255, 50, 50)},
    {"name": "COSMICO", "bg_top": (5, 15, 40), "bg_bottom": (20, 50, 90), "text_main": (180, 230, 255), "text_sub": (255, 255, 255), "text_accent": (100, 200, 255), "color_alert": (255, 100, 100)},
    {"name": "RITUAL", "bg_top": (40, 10, 10), "bg_bottom": (80, 20, 30), "text_main": (255, 215, 0), "text_sub": (255, 240, 220), "text_accent": (255, 180, 50), "color_alert": (255, 80, 80)}
]

PALETAS_TINT = [
    {"nombre": "purple", "color": (130, 43, 189), "opacity": 0.18},
    {"nombre": "blue",   "color": (15, 40, 100),  "opacity": 0.22},
    {"nombre": "wine",   "color": (90, 20, 60),   "opacity": 0.20},
    {"nombre": "teal",   "color": (15, 80, 80),   "opacity": 0.20},
    {"nombre": "indigo", "color": (50, 30, 120),  "opacity": 0.22},
]

# Significados de las cartas para que la IA no invente cualquier cosa
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
# CTAs fijos que se agregan por código al final
CTA_COMMENT = "Contame en los comentarios si esto te resuena hoy."
CTA_SAVE = "Guardá este video en favoritos para volver a verlo cuando lo necesites."
CTA_HOOK = "Si querés una carta así cada mañana, te la mando por WhatsApp."
CTA_FINAL = "Para recibir tu carta del tarot cada mañana en tu WhatsApp, suscribite en tarotgratis punto online por menos de cinco dólares al mes."

HOOK_STYLES = ["PREGUNTA_INCOMODA", "AFIRMACION_BRUTAL", "PROHIBICION", "VERDAD_DURA", "ADVERTENCIA", "REVELACION", "SECRETO", "TIEMPO_LIMITE"]

SIGN_CARD_OFFSETS = [0, 7, 14, 3, 10, 17, 4, 11, 18, 5, 12, 19]

SIGNOS = [
    {"nombre": "Aries", "emoji": "♈", "elemento": "Fuego", "tono": "impulsivo, directo", "temas": ["acción inmediata", "liderazgo", "coraje", "paciencia"]},
    {"nombre": "Tauro", "emoji": "♉", "elemento": "Tierra", "tono": "sensual, estable", "temas": ["seguridad material", "placeres simples", "constancia", "soltar"]},
    {"nombre": "Géminis", "emoji": "♊", "elemento": "Aire", "tono": "curioso, disperso", "temas": ["comunicación", "aprendizaje", "decisiones", "elegir"]},
    {"nombre": "Cáncer", "emoji": "♋", "elemento": "Agua", "tono": "emocional, protector", "temas": ["familia", "hogar", "sanar", "límites"]},
    {"nombre": "Leo", "emoji": "♌", "elemento": "Fuego", "tono": "dramático, orgulloso", "temas": ["brillar", "creatividad", "reconocimiento", "humildad"]},
    {"nombre": "Virgo", "emoji": "♍", "elemento": "Tierra", "tono": "analítico, servicial", "temas": ["orden", "salud", "servicio", "soltar perfeccionismo"]},
    {"nombre": "Libra", "emoji": "♎", "elemento": "Aire", "tono": "diplomático, indeciso", "temas": ["relaciones", "belleza", "equilibrio", "decidir"]},
    {"nombre": "Escorpio", "emoji": "♏", "elemento": "Agua", "tono": "intenso, reservado", "temas": ["transformación", "poder personal", "celos", "confiar"]},
    {"nombre": "Sagitario", "emoji": "♐", "elemento": "Fuego", "tono": "aventurero, exagerado", "temas": ["expansión", "viajes", "fe", "compromiso"]},
    {"nombre": "Capricornio", "emoji": "♑", "elemento": "Tierra", "tono": "disciplinado, frío", "temas": ["metas", "responsabilidad", "trabajo", "disfrutar"]},
    {"nombre": "Acuario", "emoji": "♒", "elemento": "Aire", "tono": "rebelde, distante", "temas": ["libertad", "innovación", "amistades", "emociones"]},
    {"nombre": "Piscis", "emoji": "♓", "elemento": "Agua", "tono": "soñador, evasivo", "temas": ["intuición", "arte", "espiritualidad", "límites"]},
]

ARCANOS = ["El Loco", "El Mago", "La Sacerdotisa", "La Emperatriz", "El Emperador", "El Hierofante", "Los Enamorados", "El Carro", "La Fuerza", "El Ermitaño", "La Rueda de la Fortuna", "La Justicia", "El Colgado", "La Muerte", "La Templanza", "El Diablo", "La Torre", "La Estrella", "La Luna", "El Sol", "El Juicio", "El Mundo"]
CARD_GLYPHS = {"El Loco": "🎭", "El Mago": "⚡", "La Sacerdotisa": "🌙", "La Emperatriz": "🌿", "El Emperador": "👑", "El Hierofante": "🕊️", "Los Enamorados": "💫", "El Carro": "⚔️", "La Fuerza": "🦁", "El Ermitaño": "🕯️", "La Rueda de la Fortuna": "☸️", "La Justicia": "⚖️", "El Colgado": "💧", "La Muerte": "🌑", "La Templanza": "✨", "El Diablo": "🔥", "La Torre": "⚡", "La Estrella": "⭐", "La Luna": "🌙", "El Sol": "☀️", "El Juicio": "🎺", "El Mundo": "🌍"}
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

def _is_too_similar(new_script: str, prev_scripts: list, umbral: float = 0.55) -> bool:
    new_set = set(w.lower().strip(".,!?¡¿;:") for w in new_script.split() if len(w) > 4)
    if not new_set: return False
    for prev in prev_scripts:
        prev_set = set(w.lower().strip(".,!?¡¿;:") for w in prev.split() if len(w) > 4)
        if not prev_set: continue
        if len(new_set & prev_set) / len(new_set | prev_set) > umbral: return True
    return False

# =====================================================================
# NUEVA LÓGICA: La IA solo escribe la lectura, el código arma el guión final
# =====================================================================
def generate_reading(signo: dict, card: str) -> dict:
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    hoy = datetime.now().strftime("%d de %B de %Y")
    
    # Le pasamos a la IA el significado de la carta y los temas del signo
    significado_carta = TAROT_MEANINGS.get(card, "transformación y crecimiento")
    temas = ", ".join(signo["temas"])
    structure = random.choice(SCRIPT_STRUCTURES)
    
    tags = ["tarot", signo['nombre'].lower(), f"tarot {signo['nombre'].lower()}", "tarot diario", "carta del día", "tarot gratis", "tarotonline", "horoscopo", signo['elemento'].lower()]

    prompt = f"""Eres un tarotista con 20 años de experiencia. Escribí el texto de una lectura para el signo {signo['nombre']}.
La carta que salió es "{card}", que significa: {significado_carta}.
AUDIENCIA: Personas de 45-64 años en Latinoamérica. Hablales de forma directa, como un consejo sabio.

ESTRUCTURA SUGERIDA: {structure} (empieza con una pregunta, una imagen, o una afirmación fuerte).

REGLAS:
1. Tono: {signo['tono']}. Hablale a UN {signo['nombre']}.
2. Mencioná sutilmente estos temas: {temas}.
3. PROHIBIDO usar clichés como: "el universo te pide", "es momento de fluir", "confía en el proceso".
4. Máximo 80 palabras.
5. NO incluyas ningún llamado a la acción (WhatsApp, comentarios, etc.), solo la lectura pura.

Devolvé SOLO un JSON válido con este formato exacto:
{{
  "title": "{signo['nombre'].upper()} HOY | {card} | Tarot",
  "lectura": "Escribí aquí el texto completo de la lectura, de 70 a 80 palabras.",
  "description": "🔮 Tarot de hoy para {signo['nombre']} con {card}. Recibí tu carta diaria en WhatsApp 👇"
}}"""

    data = None
    for intento in range(3):
        try:
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                max_tokens=400,
            )
            raw = resp.choices[0].message.content.strip()
            if "```json" in raw: raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw: raw = raw.split("```")[1].split("```")[0].strip()
                
            parsed = json.loads(raw)
            lectura = parsed.get("lectura", "")
            
            # Si la lectura tiene al menos 40 palabras, la aceptamos
            if len(lectura.split()) >= 40:
                parsed["tags"] = tags
                data = parsed
                break 
            else:
                print(f"   ⚠️ Intento {intento+1}: Lectura muy corta, reintentando...")
                
        except Exception as e:
            print(f"   ⚠️ Error de Groq: {e}")
            time.sleep(2)

    if not data:
        print("   ❌ Usando lectura de respaldo.")
        lectura_respaldo = (
            f"{signo['nombre']}, lo que estás sintiendo no es casualidad. {card} llega para mostrarte que {significado_carta} es el camino. "
            f"Dejá de buscar respuestas afuera y escuchá esa voz interna que te habla de {random.choice(signo['temas'])}. "
            f"Es momento de tomar las riendas y confiar en tu propio poder."
        )
        data = {
            "title": f"{signo['nombre'].upper()} HOY | {card} | Tarot {hoy}",
            "lectura": lectura_respaldo,
            "description": f"Tarot para {signo['nombre']} con {card}",
            "tags": tags
        }

    # ACÁ UNIMOS LA LECTURA DE LA IA CON LOS CTAs (Así nunca falla ni queda vacío)
    guion_completo = (
        f"{data['lectura']} "
        f"{CTA_COMMENT} "
        f"{CTA_SAVE} "
        f"{CTA_HOOK} "
        f"{CTA_FINAL}"
    )
    
    data["script"] = guion_completo
    return data

def generate_voice(script: str, output_path: str, elemento: str = "Fuego") -> float:
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=script)
    voice_name = os.getenv("GOOGLE_TTS_VOICE", VOCES_POR_ELEMENTO.get(elemento, "es-US-Neural2-A"))
    voice = texttospeech.VoiceSelectionParams(language_code="es-US", name=voice_name, ssml_gender=texttospeech.SsmlVoiceGender.FEMALE)

    if voice_name in VOCES_SIN_PITCH:
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=0.92, volume_gain_db=1.0)
    else:
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=0.92, pitch=-1.0, volume_gain_db=1.0)

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
    for attempt_query in queries[:2] + ["dark mystical purple"]:
        try:
            resp = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": api_key}, params={"query": attempt_query, "per_page": 10, "size": "medium"}, timeout=30)
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

def _hook_bg_gradient(w, h, color_top, color_bottom, alpha_max=230):
    bg = Image.new("RGBA", (w, h))
    for y in range(h):
        t = y / h
        bg.putpixel((0, y), (int(color_top[0]*(1-t)+color_bottom[0]*t), int(color_top[1]*(1-t)+color_bottom[1]*t), int(color_top[2]*(1-t)+color_bottom[2]*t), alpha_max))
        for x in range(w): bg.putpixel((x, y), bg.getpixel((0, y)))
    return bg

def _draw_line(draw, w, y, color, start=140, end_offset=140):
    for xi in range(start, w - end_offset):
        ga = int(220 * (1 - abs(((xi - start) / (w - start - end_offset)) * 2 - 1)))
        draw.point((xi, y), fill=(*color, ga))

def _make_hook_overlay(signo: dict, card: str) -> np.ndarray:
    w, h = VIDEO_W, VIDEO_H
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    theme = random.choice(HOOK_THEMES)
    bg = _hook_bg_gradient(w, h, theme["bg_top"], theme["bg_bottom"])
    img = Image.alpha_composite(img, bg)
    draw = ImageDraw.Draw(img)
    style = random.choice(HOOK_STYLES)
    t_main, t_sub, t_acc, t_alert = theme["text_main"], theme["text_sub"], theme["text_accent"], theme["color_alert"]

    if style == "PREGUNTA_INCOMODA":
        _draw_line(draw, w, 300, t_acc)
        for i, l in enumerate(["¿POR QUÉ", "TE SENTÍS ASÍ?"]):
            f = _fit_font_to_width(l, w-80, 76, 44)
            bbox = draw.textbbox((0, 0), l, font=f)
            x = (w - (bbox[2] - bbox[0])) // 2
            draw.text((x+4, 394+i*100+4), l, font=f, fill=(0,0,0,240)); draw.text((x, 394+i*100), l, font=f, fill=t_main)
        _draw_line(draw, w, 610, t_acc, 180, 180)
        sub = f"{signo['nombre']}, hay una razón"
        fs = _fit_font_to_width(sub, w-80, 42, 26)
        draw.text(((w-(fs.getbbox(sub)[2]-fs.getbbox(sub)[0]))//2, 652), sub, font=fs, fill=t_sub)
    elif style == "AFIRMACION_BRUTAL":
        _draw_line(draw, w, 300, t_acc)
        for i, l in enumerate([signo['nombre'].upper()+",", "ESTO NO ES", "CASUALIDAD"]):
            f = _fit_font_to_width(l, w-80, 68 if i==0 else 62, 38)
            bbox = draw.textbbox((0, 0), l, font=f)
            x = (w - (bbox[2] - bbox[0])) // 2
            draw.text((x+3, [404, 494, 574][i]+3), l, font=f, fill=(0,0,0,230)); draw.text((x, [404, 494, 574][i]), l, font=f, fill=t_main if i>0 else t_acc)
        _draw_line(draw, w, 660, t_acc, 180, 180)
        sub = f"{card} tiene algo que decirte"
        fs = _fit_font_to_width(sub, w-80, 34, 22)
        draw.text(((w-(fs.getbbox(sub)[2]-fs.getbbox(sub)[0]))//2, 700), sub, font=fs, fill=t_sub)
    elif style == "PROHIBICION":
        _draw_line(draw, w, 300, t_acc)
        for i, l in enumerate([signo['nombre'].upper()+",", "DEJÁ DE", "HACER ESTO HOY"]):
            f = _fit_font_to_width(l, w-80, 68 if i==0 else 64, 34)
            bbox = draw.textbbox((0, 0), l, font=f)
            x = (w - (bbox[2] - bbox[0])) // 2
            draw.text((x+3, [394, 484, 574][i]+3), l, font=f, fill=(0,0,0,230)); draw.text((x, [394, 484, 574][i]), l, font=f, fill=t_alert if i>0 else t_main)
        _draw_line(draw, w, 660, t_acc, 180, 180)
        sub = f"{card} te lo advierte"
        fs = _fit_font_to_width(sub, w-80, 36, 24)
        draw.text(((w-(fs.getbbox(sub)[2]-fs.getbbox(sub)[0]))//2, 700), sub, font=fs, fill=t_sub)
    elif style == "VERDAD_DURA":
        _draw_line(draw, w, 300, t_acc)
        for i, l in enumerate([signo['nombre'].upper()+",", "ESTO TE VA", "A DOLER"]):
            f = _fit_font_to_width(l, w-80, 68 if i==0 else 62, 38)
            bbox = draw.textbbox((0, 0), l, font=f)
            x = (w - (bbox[2] - bbox[0])) // 2
            draw.text((x+3, [394, 484, 564][i]+3), l, font=f, fill=(0,0,0,230)); draw.text((x, [394, 484, 564][i]), l, font=f, fill=t_main if i>0 else t_acc)
        _draw_line(draw, w, 660, t_acc, 180, 180)
        sub = "Pero necesitás escucharlo"
        fs = _fit_font_to_width(sub, w-80, 34, 22)
        draw.text(((w-(fs.getbbox(sub)[2]-fs.getbbox(sub)[0]))//2, 700), sub, font=fs, fill=t_sub)
    elif style == "ADVERTENCIA":
        _draw_line(draw, w, 300, t_acc)
        for i, l in enumerate(["CUIDADO,", signo['nombre'].upper()]):
            f = _fit_font_to_width(l, w-80, 68 if i==0 else 78, 44)
            bbox = draw.textbbox((0, 0), l, font=f)
            x = (w - (bbox[2] - bbox[0])) // 2
            draw.text((x+4, [404, 494][i]+4), l, font=f, fill=(0,0,0,240)); draw.text((x, [404, 494][i]), l, font=f, fill=t_alert)
        _draw_line(draw, w, 610, t_acc, 180, 180)
        sub = "Algo se está moviendo hoy"
        fs = _fit_font_to_width(sub, w-80, 40, 26)
        draw.text(((w-(fs.getbbox(sub)[2]-fs.getbbox(sub)[0]))//2, 652), sub, font=fs, fill=t_sub)
    elif style == "REVELACION":
        _draw_line(draw, w, 300, t_acc)
        for i, l in enumerate(["EL ERROR QUE", "COMETÉS,", signo['nombre'].upper()]):
            f = _fit_font_to_width(l, w-80, 58 if i<2 else 66, 34)
            bbox = draw.textbbox((0, 0), l, font=f)
            x = (w - (bbox[2] - bbox[0])) // 2
            draw.text((x+3, [380, 460, 540][i]+3), l, font=f, fill=(0,0,0,230)); draw.text((x, [380, 460, 540][i]), l, font=f, fill=t_main if i<2 else t_acc)
        _draw_line(draw, w, 640, t_acc, 180, 180)
        sub = f"{card} te lo revela"
        fs = _fit_font_to_width(sub, w-80, 34, 22)
        draw.text(((w-(fs.getbbox(sub)[2]-fs.getbbox(sub)[0]))//2, 680), sub, font=fs, fill=t_sub)
    elif style == "SECRETO":
        _draw_line(draw, w, 300, t_acc)
        for i, l in enumerate(["NADIE TE", "DIJO ESTO"]):
            f = _fit_font_to_width(l, w-80, 64, 38)
            bbox = draw.textbbox((0, 0), l, font=f)
            x = (w - (bbox[2] - bbox[0])) // 2
            draw.text((x+3, [404, 504][i]+3), l, font=f, fill=(0,0,0,230)); draw.text((x, [404, 504][i]), l, font=f, fill=t_main)
        _draw_line(draw, w, 620, t_acc, 180, 180)
        sub = f"La verdad sobre {signo['nombre']}"
        fs = _fit_font_to_width(sub, w-80, 40, 26)
        draw.text(((w-(fs.getbbox(sub)[2]-fs.getbbox(sub)[0]))//2, 662), sub, font=fs, fill=t_sub)
    else: # TIEMPO_LIMITE
        _draw_line(draw, w, 300, t_acc)
        for i, l in enumerate([signo['nombre'].upper()+",", "TENÉS", "HASTA HOY"]):
            f = _fit_font_to_width(l, w-80, 68 if i==0 else 64, 38)
            bbox = draw.textbbox((0, 0), l, font=f)
            x = (w - (bbox[2] - bbox[0])) // 2
            draw.text((x+3, [394, 474, 554][i]+3), l, font=f, fill=(0,0,0,230)); draw.text((x, [394, 474, 554][i]), l, font=f, fill=t_alert if i==2 else (t_acc if i==0 else t_main))
        _draw_line(draw, w, 650, t_acc, 180, 180)
        sub = f"{card} no espera"
        fs = _fit_font_to_width(sub, w-80, 36, 24)
        draw.text(((w-(fs.getbbox(sub)[2]-fs.getbbox(sub)[0]))//2, 690), sub, font=fs, fill=t_sub)

    font_sm = ImageFont.truetype(_BOLD_FONT_PATHS[0], 30) if os.path.exists(_BOLD_FONT_PATHS[0]) else ImageFont.load_default()
    hint = "Mirá hasta el final"
    bbox = draw.textbbox((0, 0), hint, font=font_sm)
    draw.text(((w-(bbox[2]-bbox[0]))//2, 800), hint, font=font_sm, fill=t_sub)
    cx = w // 2
    for i in range(3): draw.polygon([(cx - 30, 850+i*25), (cx + 30, 850+i*25), (cx, 850+i*25+22)], fill=(*t_acc, 200-i*40))
    return np.array(img)

def _make_tarot_card_visual(card: str) -> np.ndarray:
    w, h = 400, 600
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        r = int(40 * (1 - t) + 20 * t); g = int(20 * (1 - t) + 10 * t); b = int(80 * (1 - t) + 40 * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b, 240))
    draw.rectangle([(0, 0), (w-1, h-1)], outline=C_GOLD, width=6)
    draw.rectangle([(10, 10), (w-11, h-11)], outline=C_GOLD_LIGHT, width=2)
    for _ in range(40):
        x, y = random.randint(20, w-20), random.randint(20, h-20)
        draw.point((x, y), fill=(*C_GOLD_LIGHT, random.randint(100, 255)))
    glyph = CARD_GLYPHS.get(card, "✨")
    font_glyph = ImageFont.truetype(_BOLD_FONT_PATHS[0], 140) if os.path.exists(_BOLD_FONT_PATHS[0]) else ImageFont.load_default()
    bbox = draw.textbbox((0, 0), glyph, font=font_glyph)
    gx = (w - (bbox[2] - bbox[0])) // 2
    gy = (h - (bbox[3] - bbox[1])) // 2 - 50
    draw.text((gx, gy), glyph, font=font_glyph, fill=C_GOLD_LIGHT)
    card_text = card.upper()
    font_card = _fit_font_to_width(card_text, w - 40, 44, 24)
    bbox = draw.textbbox((0, 0), card_text, font=font_card)
    cx = (w - (bbox[2] - bbox[0])) // 2
    draw.text((cx, h - 120), card_text, font=font_card, fill=C_TEXT)
    return np.array(img)

def _make_title_overlay(signo: dict, card: str) -> np.ndarray:
    w, h = VIDEO_W, 390
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bg  = Image.new("RGBA", (w, h))
    for y in range(h):
        for x in range(w): bg.putpixel((x, y), (*C_BG_DEEP, int(210 * max(0, 1 - (y / h) * 1.0))))
    img  = Image.alpha_composite(img, bg)
    draw = ImageDraw.Draw(img)
    font_sign, font_card, font_url = _load_fonts(50, 32, 42)
    draw.line([(40, 16), (w - 40, 16)], fill=(*C_GOLD, 255), width=2)
    signo_text = f"-- {signo['nombre'].upper()} --"
    bbox = draw.textbbox((0, 0), signo_text, font=font_sign)
    draw.text(((w - (bbox[2]-bbox[0]))//2+2, 28), signo_text, font=font_sign, fill=(0, 0, 0, 200)); draw.text(((w - (bbox[2]-bbox[0]))//2, 26), signo_text, font=font_sign, fill=(*C_GOLD, 255))
    bbox = draw.textbbox((0, 0), card.upper(), font=font_card)
    draw.text(((w - (bbox[2]-bbox[0]))//2+2, 92), card.upper(), font=font_card, fill=(0, 0, 0, 200)); draw.text(((w - (bbox[2]-bbox[0]))//2, 90), card.upper(), font=font_card, fill=(*C_TEXT, 240))
    font_sm = _load_fonts(24, 24, 22)[2]
    bbox = draw.textbbox((0, 0), "Lectura gratis en:", font=font_sm)
    draw.text(((w - (bbox[2]-bbox[0]))//2, 150), "Lectura gratis en:", font=font_sm, fill=(*C_MUTED, 230))
    bbox = draw.textbbox((0, 0), "tarotgratis.online", font=font_url)
    draw.text(((w - (bbox[2]-bbox[0]))//2+3, 183), "tarotgratis.online", font=font_url, fill=(0, 0, 0, 240)); draw.text(((w - (bbox[2]-bbox[0]))//2, 180), "tarotgratis.online", font=font_url, fill=(*C_GOLD, 255))
    for xi in range(40, w - 40):
        ga = int(210 * (1 - abs(((xi - 40) / (w - 80)) * 2 - 1)))
        draw.point((xi, 246), fill=(*C_GOLD, ga))
    draw.point((w//2, 246), fill=(*C_GOLD_LIGHT, 255))
    return np.array(img)

def _make_cta_overlay() -> np.ndarray:
    w, h = VIDEO_W, 240
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bg = Image.new("RGBA", (w, h))
    for y in range(h):
        for x in range(w): bg.putpixel((x, y), (int(C_BG_DEEP[0]*.6), int(C_BG_DEEP[1]*.6), int(C_BG_MID[2]*.8), int(220 * (y / h))))
    img = Image.alpha_composite(img, bg)
    draw = ImageDraw.Draw(img)
    font_big, font_med, font_sm = _load_fonts(44, 30, 22)
    for x in range(w):
        t = x / w
        r = int(C_GOLD[0] + (C_GOLD_LIGHT[0] - C_GOLD[0]) * (1 - abs(t * 2 - 1)))
        g = int(C_GOLD[1] + (C_GOLD_LIGHT[1] - C_GOLD[1]) * (1 - abs(t * 2 - 1)))
        b = int(C_GOLD[2] + (C_GOLD_LIGHT[2] - C_GOLD[2]) * (1 - abs(t * 2 - 1)))
        draw.point((x, 12), fill=(r, g, b, 160))
    l1 = "📲 Tu carta del día en WhatsApp"
    bbox = draw.textbbox((0, 0), l1, font=font_sm)
    draw.text(((w - (bbox[2] - bbox[0])) // 2, 25), l1, font=font_sm, fill=(*C_TEXT, 240))
    l2 = "tarotgratis.online"
    bbox = draw.textbbox((0, 0), l2, font=font_big)
    draw.text(((w - (bbox[2] - bbox[0]))//2 + 3, 78), l2, font=font_big, fill=(0, 0, 0, 230)); draw.text(((w - (bbox[2] - bbox[0]))//2, 75), l2, font=font_big, fill=(*C_GOLD, 255))
    l3 = "Solo $4.99/mes · Cancelá cuando quieras"
    bbox = draw.textbbox((0, 0), l3, font=font_sm)
    draw.text(((w - (bbox[2] - bbox[0])) // 2, 138), l3, font=font_sm, fill=(*C_TEXT, 240))
    l4 = "👇 Suscribite en la web"
    bbox = draw.textbbox((0, 0), l4, font=font_med)
    draw.text(((w - (bbox[2] - bbox[0])) // 2, 175), l4, font=font_med, fill=(*C_GOLD_LIGHT, 255))
    return np.array(img)

def _make_mid_cta_overlay() -> np.ndarray:
    w, h = VIDEO_W, 180
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bg = Image.new("RGBA", (w, h))
    for y in range(h):
        for x in range(w): bg.putpixel((x, y), (*C_BG_DEEP, min(215, 175 + int(40 * (y / h)))))
    img = Image.alpha_composite(img, bg)
    draw = ImageDraw.Draw(img)
    font_big, font_sm = _load_fonts(50, 32, 24)[:2]
    l1 = "🌙 Tu carta diaria por WhatsApp:"
    bbox = draw.textbbox((0, 0), l1, font=font_sm)
    draw.text(((w - (bbox[2] - bbox[0])) // 2, 22), l1, font=font_sm, fill=(*C_TEXT, 245))
    l2 = "tarotgratis.online"
    bbox = draw.textbbox((0, 0), l2, font=font_big)
    draw.text(((w - (bbox[2] - bbox[0]))//2 + 3, 68), l2, font=font_big, fill=(0, 0, 0, 240)); draw.text(((w - (bbox[2] - bbox[0]))//2, 65), l2, font=font_big, fill=(*C_GOLD, 255))
    return np.array(img)

def _make_free_overlay() -> np.ndarray:
    w, h = VIDEO_W, 180
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bg = Image.new("RGBA", (w, h))
    for y in range(h):
        for x in range(w): bg.putpixel((x, y), (*C_BG_DEEP, int(220 * (y / h))))
    img = Image.alpha_composite(img, bg)
    draw = ImageDraw.Draw(img)
    font_big, font_sm = _load_fonts(40, 28, 20)[:2]
    l1 = "📲 Descarga tu carta gratis en:"
    bbox = draw.textbbox((0, 0), l1, font=font_sm)
    draw.text(((w-(bbox[2]-bbox[0]))//2, 20), l1, font=font_sm, fill=(*C_TEXT,240))
    l2 = "tarotgratis.online"
    bbox = draw.textbbox((0, 0), l2, font=font_big)
    draw.text(((w-(bbox[2]-bbox[0]))//2 + 2, 70), l2, font=font_big, fill=(0,0,0,240)); draw.text(((w-(bbox[2]-bbox[0]))//2, 68), l2, font=font_big, fill=(*C_GOLD,255))
    return np.array(img)

def _make_pricing_overlay() -> np.ndarray:
    w, h = VIDEO_W, 280
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bg = Image.new("RGBA", (w, h))
    for y in range(h):
        for x in range(w): bg.putpixel((x, y), (*C_BG_DEEP, int(220 * (y / h))))
    img = Image.alpha_composite(img, bg)
    draw = ImageDraw.Draw(img)
    font_big, font_sm = _load_fonts(52, 34, 24)[:2]
    bbox = draw.textbbox((0, 0), "$4.99 USD / mes", font=font_big)
    draw.text(((w-(bbox[2]-bbox[0]))//2 + 2, 20), "$4.99 USD / mes", font=font_big, fill=(0,0,0,240)); draw.text(((w-(bbox[2]-bbox[0]))//2, 18), "$4.99 USD / mes", font=font_big, fill=(*C_GOLD,255))
    for i, texto in enumerate(["📲 Carta del día en tu WhatsApp", "🔮 Interpretación personalizada por IA", "🔄 Cancela cuando quieras"]): draw.text((40, 90 + i * 35), texto, font=font_sm, fill=(*C_TEXT,240))
    bbox = draw.textbbox((0, 0), "tarotgratis.online", font=font_big)
    draw.text(((w-(bbox[2]-bbox[0]))//2 + 2, 210), "tarotgratis.online", font=font_big, fill=(0,0,0,240)); draw.text(((w-(bbox[2]-bbox[0]))//2, 208), "tarotgratis.online", font=font_big, fill=(*C_GOLD,255))
    return np.array(img)

def compose_video(bg_video_path, audio_path, signo, card, output_path, cta_type="none", paleta_tint=None):
    if paleta_tint is None: paleta_tint = random.choice(PALETAS_TINT)
    audio = AudioFileClip(audio_path)
    total_duration = audio.duration + 1.0

    bg = VideoFileClip(bg_video_path, audio=False)
    if bg.duration < total_duration: bg = concatenate_videoclips([bg.copy() for _ in range(int(total_duration/bg.duration)+2)])
    bg = bg.subclip(0, total_duration)

    if (bg.w / bg.h) > (VIDEO_W/VIDEO_H): bg = bg.resize(height=VIDEO_H).crop(x_center=bg.w/2, width=VIDEO_W)
    else: bg = bg.resize(width=VIDEO_W).crop(y_center=bg.h/2, height=VIDEO_H)

    card_img = ImageClip(_make_tarot_card_visual(card)).set_position(("center", "center")).set_duration(total_duration).crossfadein(0.5)

    final_clips = [
        bg, 
        ColorClip(size=(VIDEO_W, VIDEO_H), color=list(C_BG_DEEP)).set_opacity(0.40).set_duration(total_duration),
        ColorClip(size=(VIDEO_W, VIDEO_H), color=list(paleta_tint["color"])).set_opacity(paleta_tint["opacity"]).set_duration(total_duration),
        card_img,
        ImageClip(_make_hook_overlay(signo, card)).set_start(0.0).set_duration(2.0).set_position(("center", 0)).crossfadeout(0.4),
        ImageClip(_make_title_overlay(signo, card)).set_start(2.0).set_duration(total_duration - 2.0).set_position(("center", 60)).crossfadein(0.4),
        ImageClip(_make_mid_cta_overlay()).set_start(total_duration*0.40).set_duration(6.0).set_position(("center", int(VIDEO_H*0.50))).crossfadein(0.8).crossfadeout(0.8),
        ImageClip(_make_cta_overlay()).set_start(max(1.0, total_duration - 7)).set_duration(total_duration - max(1.0, total_duration - 7)).set_position(("center", int(VIDEO_H * 0.38))).crossfadein(1.0)
    ]

    if cta_type == "paid": final_clips.append(ImageClip(_make_pricing_overlay()).set_start(max(1.0, total_duration - 5.0)).set_duration(5.0).set_position(("center", int(VIDEO_H * 0.30))).crossfadein(0.8))
    elif cta_type == "free": final_clips.append(ImageClip(_make_free_overlay()).set_start(max(1.0, total_duration - 4.0)).set_duration(4.0).set_position(("center", int(VIDEO_H * 0.42))).crossfadein(0.8))

    TEMP_DIR.mkdir(exist_ok=True)
    final = CompositeVideoClip(final_clips, size=(VIDEO_W, VIDEO_H)).set_audio(audio)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    final.write_videofile(output_path, fps=FPS, codec="libx264", audio_codec="aac", temp_audiofile=str(TEMP_DIR / f"tmp_{Path(output_path).stem}.m4a"), remove_temp=True, threads=2, preset="ultrafast", verbose=False, logger=None)
    
    for clip in [audio, bg, final]:
        try: clip.close()
        except: pass
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

    if prev_scripts and _is_too_similar(reading["script"], prev_scripts):
        print(f"   ⚠️  Guión similar, regenerando UNA VEZ...")
        time.sleep(6)
        new_reading = generate_reading(signo, card)
        if not _is_too_similar(new_reading["script"], prev_scripts): reading = new_reading

    print(f"    {reading['title']}")
    audio_path = str(TEMP_DIR / f"{slug}.mp3")
    print("🎙️   Generando voz...")
    duration = generate_voice(reading["script"], audio_path, signo["elemento"])
    print(f"    {duration:.1f}s")

    bg_path = str(TEMP_DIR / f"{slug}_bg.mp4")
    print("🎬  Descargando fondo Pexels...")
    if not download_pexels_video(card, bg_path): raise RuntimeError(f"No se pudo descargar fondo para {signo['nombre']}")

    output_path = str(OUTPUT_DIR / f"{slug}.mp4")
    print(f"🎞️   Componiendo video con CTA: {cta_type}")
    compose_video(bg_path, audio_path, signo, card, output_path, cta_type, paleta)
    print(f"✅  {signo['nombre']} listo: {output_path}")

    return {
        "video_path": output_path, "title": reading["title"], "description": reading["description"],
        "tags": reading["tags"], "script": reading["script"], "signo": signo["nombre"],
        "card": card, "duration_s": duration, "cta_type": cta_type, "paleta": paleta["nombre"],
    }