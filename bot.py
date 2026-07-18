import requests
import telebot

# Coloca aquí tu Token de Telegram real entre las comillas
TOKEN_TELEGRAM = "8632019517:AAHMlr_OuSYBfjPVWyUuFXHWTNf8OeIehI4"
bot = telebot.TeleBot(TOKEN_TELEGRAM)

MONTO_USD_FILTRO = 500.0  # Capital de referencia base fijo en dólares

def obtener_tasa_bcv_real():
    """
    Obtiene de forma automatizada la tasa oficial en dólares del BCV.
    Si el lector principal falla, recurre a una API global de respaldo.
    """
    url_bcv = "https://pydolarvenezuela-api.vercel.app/api/v1/dollar?page=bcv"
    try:
        res = requests.get(url_bcv, timeout=5)
        datos = res.json()
        return float(datos["monedas"]["usd"]["price"])
    except Exception:
        try:
            res_alt = requests.get("https://open.er-api.com/v6/latest/USD", timeout=5).json()
            return float(res_alt["rates"]["VES"])
        except Exception as e:
            print(f"Error crítico al conectar con la tasa cambiaria: {e}")
            return None

def obtener_tasa_binance_p2p(tipo_operacion, monto_ves_filtro):
    """
    Consulta el libro de órdenes real de Binance P2P filtrando por monto
    y exigiendo de forma estricta ÚNICAMENTE comerciantes verificados.
    """
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    trade_type = "BUY" if tipo_operacion.lower() == "compra" else "SELL"
    
    payload = {
        "asset": "USDT",
        "fiat": "VES",
        "merchantCheck": False,
        "page": 1,
        "payTypes": [],
        "publisherType": "merchant",  # Exige solo comerciantes verificados (Check amarillo)
        "rows": 1,
        "tradeType": trade_type,
        "transAmount": str(int(monto_ves_filtro))  # Filtro dinámico según la tasa del día
    }
    
    try:
        res = requests.post(url, json=payload, timeout=8)
        data = res.json()
        if data and "data" in data and len(data["data"]) > 0:
            return float(data["data"][0]["adv"]["price"])
    except Exception as e:
        print(f"Error en consulta Binance P2P: {e}")
    return None

@bot.message_handler(commands=['precio'])
def enviar_precio(message):
    # 1. Obtener la tasa oficial del día de manera automática
    tasa_bcv_cruda = obtener_tasa_bcv_real()
    
    if not tasa_bcv_cruda:
        bot.reply_to(message, "❌ Error temporal al conectar con la tasa base. Intenta en unos segundos.")
        return

    # 2. Aplicar el ajuste del +0.5% sobre la tasa del día
    tasa_bcv_ajustada = tasa_bcv_cruda * 1.005
    
    # 3. Calcular los bolívares requeridos para mover los $500 base
    monto_ves_filtro = MONTO_USD_FILTRO * tasa_bcv_ajustada

    # 4. Traer precios del P2P correspondientes a comerciantes verificados
    compra = obtener_tasa_binance_p2p("compra", monto_ves_filtro)
    venta = obtener_tasa_binance_p2p("venta", monto_ves_filtro)
    
    if compra and venta:
        spread = venta - compra
        porcentaje_ganancia = (spread / compra) * 100
        
        texto = (
            f"📊 **Tasas P2P Filtradas (${MONTO_USD_FILTRO})**\n"
            f"🏛️ BCV Oficial: {tasa_bcv_cruda:.2f} VES\n"
            f"⚙️ BCV + 0.5%: {tasa_bcv_ajustada:.2f} VES\n"
            f"🔍 Filtro de Orden: {monto_ves_filtro:,.2f} VES\n\n"
            f"🟢 Compra (Pagar): {compra} VES\n"
            f"🔴 Venta (Recibir): {venta} VES\n\n"
            f"📉 **Spread de Arbitraje:** {spread:.2f} VES ({porcentaje_ganancia:.2f}%)\n"
            f"🛡️ *Filtro: Solo Anunciantes Verificados.*"
        )
    else:
        texto = "❌ No se pudieron obtener los datos de Binance para este volumen verificado."
        
    bot.reply_to(message, texto, parse_mode="Markdown")

if __name__ == "__main__":
    print("🚀 Bot 100% automatizado y verificado activo en Railway...")
    bot.infinity_polling()
        
