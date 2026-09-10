def _make_cta_overlay() -> np.ndarray:
    """
    Overlay final optimizado para conversión:
    - Beneficio (WhatsApp diario)
    - URL (grande y visible)
    - Precio ($4.99/mes)
    - Llamado a la acción
    """
    w, h = VIDEO_W, 240  # Más alto para 4 líneas
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

    # Línea decorativa superior
    for x in range(w):
        t = x / w
        r = int(C_GOLD[0] + (C_GOLD_LIGHT[0] - C_GOLD[0]) * (1 - abs(t * 2 - 1)))
        g = int(C_GOLD[1] + (C_GOLD_LIGHT[1] - C_GOLD[1]) * (1 - abs(t * 2 - 1)))
        b = int(C_GOLD[2] + (C_GOLD_LIGHT[2] - C_GOLD[2]) * (1 - abs(t * 2 - 1)))
        draw.point((x, 12), fill=(r, g, b, 160))

    # ── Línea 1: Beneficio ────────────────────────────────────────────
    line1 = "📲 Tu carta del día en WhatsApp"
    bbox = draw.textbbox((0, 0), line1, font=font_sm)
    draw.text(((w - (bbox[2] - bbox[0])) // 2, 25), line1, font=font_sm, fill=WHITE_A)

    # ── Línea 2: URL (grande) ─────────────────────────────────────────
    line2 = "tarotgratis.online"
    bbox = draw.textbbox((0, 0), line2, font=font_big)
    x = (w - (bbox[2] - bbox[0])) // 2
    draw.text((x + 3, 78), line2, font=font_big, fill=(0, 0, 0, 230))
    draw.text((x, 75), line2, font=font_big, fill=GOLD_A)

    # ── Línea 3: Precio ──────────────────────────────────────────────
    line3 = "Solo $4.99/mes · Cancelá cuando quieras"
    bbox = draw.textbbox((0, 0), line3, font=font_sm)
    draw.text(((w - (bbox[2] - bbox[0])) // 2, 138), line3, font=font_sm, fill=WHITE_A)

    # ── Línea 4: CTA final ───────────────────────────────────────────
    line4 = "👇 Suscribite en la web"
    bbox = draw.textbbox((0, 0), line4, font=font_med)
    draw.text(((w - (bbox[2] - bbox[0])) // 2, 175), line4, font=font_med, fill=GOLD_L)

    return np.array(img)