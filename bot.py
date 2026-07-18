import requests
import telebot

# Coloca aquí tu Token de Telegram real entre las comillas
TOKEN_TELEGRAM = "8632019517:AAHEegmOwcC35emzY5q75o6NUbs704cMD6g"
bot = telebot.TeleBot(TOKEN_TELEGRAM)

MONTO_USD_FILTRO = 500.0  # Capital de referencia base fijo en dólares

# ==========================================
#  TEXTOS ESTRATÉGICOS DE ARBITRAJE DEL CANAL
# ==========================================

TEXTO_BPAY = (
    "💳 **Estrategia BPay: Carga de USD Bancarios a Binance**\n\n"
    "Este método te permite meter tus USD de intervención del banco nacional a la plataforma para generar ganancias en USDT:\n\n"
    "⚠️ **Costos Fijos:** Comisión de **3.6% a 4.1%** por depósito con tarjetas nacionales en moneda extranjera.\n\n"
    "📌 **Pasos para la Operación:**\n"
    "1️⃣ Adquiere tus dólares por intervención en tu banco nacional (BDV, Provincial, Banesco, etc.).\n"
    "2️⃣ Ve a la plataforma, selecciona la opción de **Depósito en USD (Fiat)** mediante tarjeta de débito o crédito.\n"
    "3️⃣ Introduce los datos de la tarjeta MasterCard de tu cuenta nacional en divisas. Se te debitará el monto en USD sumando la comisión fija de la pasarela.\n"
    "4️⃣ Una vez reflejado tu saldo Fiat, conviértelo directamente a **USDT** dentro de la plataforma.\n\n"
    "🔥 **Finalidad:** Al tener tus USDT, usa nuestro comando `/precio` para evaluar la tasa de venta actual en el P2P y liquidar en bolívares, asegurando tu margen de ganancia sobre la tasa base del BCV."
)

TEXTO_GPAY = (
    "📱 **Estrategia GPay: Carga de USD Bancarios a Binance**\n\n"
    "Una ruta alternativa y rápida utilizando la pasarela de Google para procesar tus dólares de intervención:\n\n"
    "⚠️ **Costos Fijos:** Comisión fija del **4.1%** por el procesamiento del método.\n\n"
    "📌 **Pasos para la Operación:**\n"
    "1️⃣ Compra tus USD oficiales en la banca nacional a tasa de intervención del BCV.\n"
    "2️⃣ Vincula la tarjeta internacional/nacional en divisas de tu banco a tu billetera de Google Pay (GPay).\n"
    "3️⃣ En la plataforma, selecciona la opción de Deposito USD  utilizando **GPay** como procesador instantáneo.\n"
    "4️⃣ Con los USD Fiat ya disponibles, realiza el intercambio desde trade (convertir) a **USDT**.\n\n"
    "🔥 **Finalidad:** Saltarse el P2P de compra para obtener el USDT mucho más económico. El beneficio real se consolida al vender esos USDT en el P2P de salida utilizando los precios verificados que te da el comando `/precio`."
)

# ==========================================
#          LÓGICA DE CONSULTAS API
# ==========================================

def obtener_tasa_bcv_real():
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
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    trade_type = "BUY" if tipo_operacion.lower() == "compra" else "SELL"
    
    payload = {
        "asset": "USDT",
        "fiat": "VES",
        "merchantCheck": False,
        "page": 1,
        "payTypes": [],
        "publisherType": "merchant",
        "rows": 1,
        "tradeType": trade_type,
        "transAmount": str(int(monto_ves_filtro))
    }
    
    try:
        res = requests.post(url, json=payload, timeout=8)
        data = res.json()
        if data and "data" in data and len(data["data"]) > 0:
            return float(data["data"][0]["adv"]["price"])
    except Exception as e:
        print(f"Error en consulta Binance P2P: {e}")
    return None

# ==========================================
#           MANEJADORES DE COMANDOS
# ==========================================

@bot.message_handler(commands=['precio'])
def enviar_precio(message):
    tasa_bcv_cruda = obtener_tasa_bcv_real()
    if not tasa_bcv_cruda:
        bot.reply_to(message, "❌ Error temporal al conectar con la tasa base. Intenta en unos segundos.")
        return

    tasa_bcv_ajustada = tasa_bcv_cruda * 1.005
    monto_ves_filtro = MONTO_USD_FILTRO * tasa_bcv_ajustada

    compra = obtener_tasa_binance_p2p("compra", monto_ves_filtro)
    venta = obtener_tasa_binance_p2p("venta", monto_ves_filtro)
    
    if compra and venta:
        spread = venta - compra
        porcentaje_ganancia = (spread / compra) * 100
        
        texto = (
            f"📊 **Tasas P2P Trade (${MONTO_USD_FILTRO})**\n"
            f"🏛️ BCV Oficial: {tasa_bcv_cruda:.2f} Bs\n"
            f"⚙️ BCV + 0.5%: {tasa_bcv_ajustada:.2f} Bs\n"
            f"🔍 Filtro de Orden: {monto_ves_filtro:,.2f} VES\n\n"
            f"🟢 Compra: {compra} Bs\n"
            f"🔴 Venta: {venta} Bs\n\n"
            f"📉 **Spread de Arbitraje:** {spread:.2f} VES ({porcentaje_ganancia:.2f}%)\n"
            f"🛡️ *Filtro: Solo Anunciantes Verificados.*"
        )
    else:
        texto = "❌ No se pudieron obtener los datos de Binance para este volumen verificado."
        
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(commands=['bpay'])
def enviar_guia_bpay(message):
    bot.reply_to(message, TEXTO_BPAY, parse_mode="Markdown")

@bot.message_handler(commands=['gpay'])
def enviar_guia_gpay(message):
    bot.reply_to(message, TEXTO_GPAY, parse_mode="Markdown")

# EL BLOQUE DE TEXTO LIBRE HA SIDO ELIMINADO PARA EVITAR CONGESTIÓN EN CANALES.

if __name__ == "__main__":
    print("🚀 Bot silencioso y enfocado en comandos activo en Railway...")
    bot.infinity_polling()
    
