# ==========================================
# emojis.py - CENTRAL DE EMOJIS ANIMADOS
# ==========================================

TG_EMOJIS = {
    # --- Emojis para Monitores y Avisos ---
    "MONITOR": "5193177581088755275", # 💻
    "CALENDARIO": "5413879192267805083", # 🗓
    "BCV": "5183805089766123191", # 🤝
    "BINANCE_P2P": "5032421268470924703", # 🟡
    "BINANCE_ESPEJO": "5384321407725358581", # 💵
  
    # --- Emojis para Arbitraje y Calculadora ---
    "calc": "5303214794236125778",
    "usdt1": "5843796824367832872",
    "check": "5206607081334906820",
    "pro": "4949492420392781701",
    "bdv1": "4945813911579788830",
    "bdv2": "4949567234420110351",
    "teso": "4949973031528170774",
    "clic": "5310278924616356636",
    "dolar": "5409048419211682843", # 💵
    
    # --- Emojis para Soporte / Pagos ---
    "paypal": "6318565240866867228", # 🌐
    "github": "5417836094098007862", # 🐱
}

def e(key, fallback=""):
    """
    Retorna la etiqueta HTML <tg-emoji> lista para concatenar.
    Si la clave no existe, devuelve solo el fallback.
    """
    emoji_id = TG_EMOJIS.get(key, "")
    if emoji_id:
        return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
    return fallback
  
