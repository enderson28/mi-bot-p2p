import requests
import telebot

# Coloca aquí tu Token de Telegram real entre las comillas
TOKEN_TELEGRAM = "8632019517:AAHEegmOwcC35emzY5q75o6NUbs704cMD6g"
bot = telebot.TeleBot(TOKEN_TELEGRAM)

# ==========================================
#  TEXTOS ESTRATÉGICOS DE ARBITRAJE DEL CANAL
# ==========================================

TEXTO_BPAY = (
    "💳 **Estrategia BPay: Carga de USD Bancarios a Binance**\n\n"
    "Este método te permite meter tus USD de intervención del banco nacional a la plataforma para generar ganancias en USDT:\n\n"
    "⚠️ **Costos Fijos:** Comisión de `3.6%` a `4.1%` por depósito con tarjetas nacionales en moneda extranjera.\n\n"
    "📌 **Pasos para la Operación:**\n"
    "1️⃣ Adquiere tus dólares por intervención en tu banco nacional (BDV, Provincial, Banesco, etc.).\n"
    "2️⃣ Ve a la plataforma, selecciona la opción de **Depósito en USD (Fiat)** mediante tarjeta de crédito o débito.\n"
    "3️⃣ Introduce los datos de tu tarjeta.\n\n"
    "🚨 **PUNTO CLAVE (Evita Bloqueos):** El banco nacional deduce una comisión interna que Binance NO calcula en su pantalla. Para evitar que el banco rechace la operación por fondos insuficientes y bloquee tu tarjeta, debes restar estos porcentajes al saldo total de tu cuenta antes de colocar el monto en BPay:\n"
    "• **BDV MasterCard (Maestro):** Restar `1.5%`\n"
    "• **BDV Tarjeta Internacional:** Restar `2.5%`\n"
    "• **Banco del Tesoro:** Restar `2.5%`\n"
    "• **Provincial (BBVA):** No cobra comisión, pero se recomienda dejar un margen fijo de `3$` a `5$` en la cuenta para evitar errores.\n\n"
    "👉 _Coloca en BPay únicamente el resultado neto de esa resta._\n\n"
    "4️⃣ Con tus USD Fiat ya disponibles, realiza el intercambio desde trade (convertir) a **USDT**.\n\n"
    "🔥 **Finalidad:** Al tener tus USDT, usa nuestro comando `/precio` para evaluar la tasa de venta actual en el P2P y liquidar en bolívares, asegurando tu margen de ganancia sobre la tasa base del BCV."
)

TEXTO_GPAY = (
    "📱 **Estrategia GPay: Carga de USD Bancarios a Binance**\n\n"
    "Una ruta alternativa y rápida utilizando la pasarela de Google para procesar tus dólares de intervención:\n\n"
    "⚠️ **Costos Fijos:** Comisión fija del `4.1%` por el procesamiento del método.\n\n"
    "📌 **Pasos para la Operación:**\n"
    "1️⃣ Compra tus USD oficiales en la banca nacional a tasa de intervención del BCV.\n"
    "2️⃣ Vincula la tarjeta internacional/nacional en divisas de tu banco a tu billetera de Google Pay (GPay).\n"
    "3️⃣ En la plataforma, selecciona la opción de **Depósito USD** utilizando **GPay** como procesador instantáneo.\n\n"
    "🚨 **PUNTO CLAVE (Evita Bloqueos):** El banco nacional deduce una comisión interna que Binance NO calcula en su pantalla. Para evitar que el banco rechace la operación por fondos insuficientes y bloquee tu tarjeta, debes restar estos porcentajes al saldo total de tu cuenta antes de colocar el monto en GPay:\n"
    "• **BDV MasterCard (Maestro):** Restar `1.5%`\n"
    "• **BDV Tarjeta Internacional:** Restar `2.5%`\n"
    "• **Banco del Tesoro:** Restar `2.5%`\n"
    "• **Provincial (BBVA):** No cobra comisión, pero se recomienda dejar un margen fijo de `3$` a `5$` en la cuenta para evitar errores.\n\n"
    "👉 _Coloca en GPay únicamente el resultado neto de esa resta._\n\n"
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

    # 1. CONSULTA PARA FILTRO CAPITALES BAJOS ($50 a $100)
    filtro_50 = 50.0 * tasa_bcv_ajustada
    c_50 = obtener_tasa_binance_p2p("compra", filtro_50)
    v_50 = obtener_tasa_binance_p2p("venta", filtro_50)

    # 2. CONSULTA PARA FILTRO CAPITALES MEDIOS ($100 a $300)
    filtro_150 = 150.0 * tasa_bcv_ajustada
    c_150 = obtener_tasa_binance_p2p("compra", filtro_150)
    v_150 = obtener_tasa_binance_p2p("venta", filtro_150)

    # 3. CONSULTA PARA FILTRO INSTITUCIONAL ($500+)
    filtro_500 = 500.0 * tasa_bcv_ajustada
    c_500 = obtener_tasa_binance_p2p("compra", filtro_500)
    v_500 = obtener_tasa_binance_p2p("venta", filtro_500)
    
    # Construcción del bloque de texto principal
    texto = (
        f"📊 **Monitor de Tasas Arbitraje P2P**\n"
        f"🏛️ BCV Oficial: `{tasa_bcv_cruda:.2f} Bs`\n"
        f"⚙️ BCV + 0.5%: `{tasa_bcv_ajustada:.2f} Bs`\n"
        f"🛡️ _Filtros activos: Solo Anunciantes Verificados_\n"
        f"----------------------------------------\n\n"
    )

    # Añadir bloque de $50-$100
    if c_50 and v_50:
        s_50 = v_50 - c_50
        p_50 = (s_50 / c_50) * 100
        texto += (
            f"🔹 **Rango Pequeño ($50 - $100)**\n"
            f"🟢 Compra: `{c_50:.2f} Bs` | 🔴 Venta: `{v_50:.2f} Bs`\n"
            f"📉 Spread: `{s_50:.2f} Bs` (`{p_50:.2f}%`)\n\n"
        )
    else:
        texto += "🔹 **Rango Pequeño ($50 - $100):** _No hay anunciantes activos_\n\n"

    # Añadir bloque de $100-$300
    if c_150 and v_150:
        s_150 = v_150 - c_150
        p_150 = (s_150 / c_150) * 100
        texto += (
            f"🔹 **Rango Mediano ($100 - $300)**\n"
            f"🟢 Compra: `{c_150:.2f} Bs` | 🔴 Venta: `{v_150:.2f} Bs`\n"
            f"📉 Spread: `{s_150:.2f} Bs` (`{p_150:.2f}%`)\n\n"
        )
    else:
        texto += "🔹 **Rango Mediano ($100 - $300):** _No hay anunciantes activos_\n\n"

    # Añadir bloque institucional de $500
    if c_500 and v_500:
        s_500 = v_500 - c_500
        p_500 = (s_500 / c_500) * 100
        texto += (
            f"🔸 **Rango Mayor ($500+)**\n"
            f"🟢 Compra: `{c_500:.2f} Bs` | 🔴 Venta: `{v_500:.2f} Bs`\n"
            f"📉 Spread: `{s_500:.2f} Bs` (`{p_500:.2f}%`)\n"
        )
    else:
        texto += "🔸 **Rango Mayor ($500+):** _No hay anunciantes activos_"

    # ==========================================
    #      ANÁLISIS Y ENUNCIADO EDUCATIVO
    # ==========================================
    texto += (
        f"\n----------------------------------------\n"
        f"💡 **REGLA DE ORO PARA GENERAR GANANCIAS**\n\n"
        f"⚠️ **¿Quieres comerciar? No compres USDT en el P2P:**\n"
        f"Usar la opción de `🟢 Compra P2P` reduce casi a cero tu margen de ganancia comercial. El verdadero beneficio se obtiene haciendo la ruta institucional.\n\n"
        f"📌 **Excepción (Uso como Ahorro):**\n"
        f"Si deseas comprar USDT por el arbitraje de `🟢 Compra`, también es perfectamente viable siempre y cuando tengas en cuenta que será una inversión estable sin margen de ganancias al momento (un tipo de ahorro en criptoactivo), porque no estás comprando al USDT oficial sino al paralelo de arbitraje.\n\n"
        f"🔄 **La Ruta para Arbitraje Activo:**\n"
        f"1️⃣ Adquiere USD oficiales en tu banco a tasa BCV.\n"
        f"2️⃣ Pásalos a Binance mediante `/bpay` o `/gpay` (Depósito USD).\n"
        f"3️⃣ Convierte a USDT y vende usando la tasa de `🔴 Venta` de este monitor.\n\n"
        f"🛡️ **Estrategia de Capital Seguro:**\n"
        f"Al vender en VES, consulta mañana este bot. Usa solo los bolívares necesarios para volver a comprar tu capital base en el banco (`BCV + 0.5%`). **¡Deja tus ganancias acumuladas en USDT dentro de Binance como tu colchón de ahorro seguro!**"
    )

    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(commands=['bpay'])
def enviar_guia_bpay(message):
    bot.reply_to(message, TEXTO_BPAY, parse_mode="Markdown")

@bot.message_handler(commands=['gpay'])
def enviar_guia_gpay(message):
    bot.reply_to(message, TEXTO_GPAY, parse_mode="Markdown")

if __name__ == "__main__":
    print("🚀 Bot multi-filtro y educativo activo en Railway...")
    bot.infinity_polling()
                 
