import requests
import telebot
import time

# ==========================================
# CONFIGURACIÓN Y TOKEN
# ==========================================
# Coloca aquí tu Token de Telegram real entre las comillas
TOKEN_TELEGRAM = "8632019517:AAHEegmOwcC35emzY5q75o6NUbs704cMD6g"
bot = telebot.TeleBot(TOKEN_TELEGRAM)

# CONFIGURACIÓN DEL NOMBRE DE TU BOT (Reemplaza con el alias real de tu bot sin el @)
BOT_USERNAME = "BancoIDV_bot" 

# Configuración de límites (Cooldown)
RATE_LIMIT = 120  # Segundos de espera para usuarios corrientes (2 minutos)
usuarios_tiempo = {} 

# ==========================================
#  TEXTOS ESTRATÉGICOS DE ARBITRAJE DEL CANAL
# ==========================================

TEXTO_START = (
    "👋 **¡Bienvenido al Monitor Oficial de Arbitraje P2P!**\n\n"
    "Este bot es tu herramienta aliada para proteger tu capital y generar ganancias reales en Venezuela 🇻🇪. "
    "Aquí no tienes que adivinar; el sistema calcula todo por ti.\n\n"
    "🚀 **¿Cómo empezar? Usa estos comandos:**\n"
    "🔹 `/precio` — Muestra las tasas reales BCV, precios P2P (pequeño, medio y alto) y la regla de oro para no perder dinero.\n"
    "🔹 `/bpay` — Guía paso a paso para cargar USD bancarios a Binance con tarjeta nacional.\n"
    "🔹 `/gpay` — Ruta alternativa para fonear usando Google Pay de forma rápida.\n\n"
    "💡 _Nota: Si eres nuevo, lee con atención la 'Regla de Oro' al final del comando /precio. ¡Evita comprar costoso en el P2P!_"
)

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

TEXTO_REGLA_ORO = (
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

def es_administrador(chat_id, user_id):
    try:
        miembros_admin = bot.get_chat_administrators(chat_id)
        for admin in miembros_admin:
            if admin.user.id == user_id:
                return True
    except Exception:
        return False
    return False

def construir_monitor_texto_html():
    """Version HTML limpia de los datos para evitar fallas por guiones bajos"""
    tasa_bcv_cruda = obtener_tasa_bcv_real()
    if not tasa_bcv_cruda:
        return "❌ Error temporal al conectar con la tasa base. Intenta en unos segundos."

    tasa_bcv_ajustada = tasa_bcv_cruda * 1.005

    filtro_50 = 50.0 * tasa_bcv_ajustada
    c_50 = obtener_tasa_binance_p2p("compra", filtro_50)
    v_50 = obtener_tasa_binance_p2p("venta", filtro_50)

    filtro_150 = 150.0 * tasa_bcv_ajustada
    c_150 = obtener_tasa_binance_p2p("compra", filtro_150)
    v_150 = obtener_tasa_binance_p2p("venta", filtro_150)

    filtro_500 = 500.0 * tasa_bcv_ajustada
    c_500 = obtener_tasa_binance_p2p("compra", filtro_500)
    v_500 = obtener_tasa_binance_p2p("venta", filtro_500)
    
    texto = (
        f"📊 <b>Monitor de Tasas Arbitraje P2P</b>\n"
        f"🏛️ BCV Oficial: {tasa_bcv_cruda:.2f} VES\n"
        f"⚙️ BCV + 0.5%: {tasa_bcv_ajustada:.2f} VES\n"
        f"🛡️ <i>Filtros activos: Solo Anunciantes Verificados</i>\n"
        f"----------------------------------------\n\n"
    )

    if c_50 and v_50:
        s_50 = v_50 - c_50
        p_50 = (s_50 / c_50) * 100
        texto += (
            f"🔹 <b>Rango Pequeño ($50 - $100)</b>\n"
            f"🟢 Compra: {c_50:.2f} Bs | 🔴 Venta: {v_50:.2f} Bs\n"
            f"📉 Spread: {s_50:.2f} Bs ({p_50:.2f}%)\n\n"
        )
    else:
        texto += "🔹 <b>Rango Pequeño ($50 - $100):</b> <i>No hay anunciantes activos</i>\n\n"

    if c_150 and v_150:
        s_150 = v_150 - c_150
        p_150 = (s_150 / c_150) * 100
        texto += (
            f"🔹 <b>Rango Mediano ($100 - $300)</b>\n"
            f"🟢 Compra: {c_150:.2f} Bs | 🔴 Venta: {v_150:.2f} Bs\n"
            f"📉 Spread: {s_150:.2f} Bs ({p_150:.2f}%)\n\n"
        )
    else:
        texto += "🔹 <b>Rango Mediano ($100 - $300):</b> <i>No hay anunciantes activos</i>\n\n"

    if c_500 and v_500:
        s_500 = v_500 - c_500
        p_500 = (s_500 / c_500) * 100
        texto += (
            f"🔸 <b>Rango Mayor ($500+)</b>\n"
            f"🟢 Compra: {c_500:.2f} Bs | 🔴 Venta: {v_500:.2f} Bs\n"
            f"📉 Spread: {s_500:.2f} Bs ({p_500:.2f}%)\n\n"
        )
    else:
        texto += "🔸 <b>Rango Mayor ($500+):</b> <i>No hay anunciantes activos</i>"

    return texto

# ==========================================
#           MANEJADORES DE COMANDOS
# ==========================================

@bot.message_handler(commands=['start'])
def handle_start(message):
    if message.chat.type == "private":
        bot.reply_to(message, TEXTO_START, parse_mode="Markdown")

@bot.message_handler(commands=['precio'])
def handle_precio(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # 1. --- CHAT PRIVADO ---
    if message.chat.type == "private":
        # Usamos la estructura clásica en privado
        try:
            tasa_bcv_cruda = obtener_tasa_bcv_real()
            tasa_bcv_ajustada = tasa_bcv_cruda * 1.005
            filtro_50, filtro_150, filtro_500 = 50.0 * tasa_bcv_ajustada, 150.0 * tasa_bcv_ajustada, 500.0 * tasa_bcv_ajustada
            c_50 = obtener_tasa_binance_p2p("compra", filtro_50)
            v_50 = obtener_tasa_binance_p2p("venta", filtro_50)
            c_150 = obtener_tasa_binance_p2p("compra", filtro_150)
            v_150 = obtener_tasa_binance_p2p("venta", filtro_150)
            c_500 = obtener_tasa_binance_p2p("compra", filtro_500)
            v_500 = obtener_tasa_binance_p2p("venta", filtro_500)
            
            texto_p = (
                f"📊 **Monitor de Tasas Arbitraje P2P**\n"
                f"🏛️ BCV Oficial: `{tasa_bcv_cruda:.2f} VES`\n"
                f"⚙️ BCV + 0.5%: `{tasa_bcv_ajustada:.2f} VES`\n"
                f"🛡️ _Filtros activos: Solo Anunciantes Verificados_\n"
                f"----------------------------------------\n\n"
                f"🔹 **Rango Pequeño ($50 - $100)**\n🟢 Compra: `{c_50:.2f} VES` | 🔴 Venta: `{v_50:.2f} VES`\n📉 Spread: `{v_50-c_50:.2f} VES` (`{((v_50-c_50)/c_50)*100:.2f}%`)\n\n"
                f"🔹 **Rango Mediano ($100 - $300)**\n🟢 Compra: `{c_150:.2f} VES` | 🔴 Venta: `{v_150:.2f} VES`\n📉 Spread: `{v_150-c_150:.2f} VES` (`{((v_150-c_150)/c_150)*100:.2f}%`)\n\n"
                f"🔸 **Rango Mayor ($500+)**\n🟢 Compra: `{c_500:.2f} VES` | 🔴 Venta: `{v_500:.2f} VES`\n📉 Spread: `{v_500-c_500:.2f} VES` (`{((v_500-c_500)/c_500)*100:.2f}%`)\n"
            )
            bot.reply_to(message, texto_p + TEXTO_REGLA_ORO, parse_mode="Markdown")
        except Exception:
            bot.reply_to(message, "❌ Error al generar la consulta privada.")
        return

    # 2. --- DENTRO DEL GRUPO ---
    if es_administrador(chat_id, user_id):
        try:
            bot.reply_to(message, construir_monitor_texto_html(), parse_mode="HTML")
        except Exception as e:
            bot.reply_to(message, "❌ Error en consulta de administrador.")
    else:
        ahora = time.time()
        ultima_vez = usuarios_tiempo.get(user_id, 0)
        
        if ahora - ultima_vez < RATE_LIMIT:
            espera = int(RATE_LIMIT - (ahora - ultima_vez))
            bot.reply_to(message, f"⏳ <b>Modo ahorro de chat:</b> Por favor espera {espera} segundos para volver a consultar en el grupo. O consulta en mi chat privado sin restricciones.", parse_mode="HTML")
        else:
            try:
                # Buscamos los precios formateados en HTML limpio
                monitor_html = construir_monitor_texto_html()
                
                # Armamos la estructura usando etiquetas HTML seguras (<b> e <i>)
                texto_grupo_usuario = monitor_html + (
                    f"\n----------------------------------------\n"
                    f"💡 <b>¿Eres nuevo en el arbitraje?</b>\n"
                    f"Para conocer la <b>Regla de Oro</b> y aprender a generar ganancias reales usando este monitor, consulta este comando en mi chat privado: @{BOT_USERNAME}"
                )
                
                # Enviamos el mensaje procesado en HTML
                bot.reply_to(message, texto_grupo_usuario, parse_mode="HTML")
                usuarios_tiempo[user_id] = ahora
                
            except Exception as e:
                bot.reply_to(message, "⚠️ Ocurrió un inconveniente temporal procesando los datos. Reintenta el comando por favor.")

@bot.message_handler(commands=['bpay', 'gpay'])
def handle_guias(message):
    if message.chat.type == "private":
        if 'bpay' in message.text:
            bot.reply_to(message, TEXTO_BPAY, parse_mode="Markdown")
        else:
            bot.reply_to(message, TEXTO_GPAY, parse_mode="Markdown")
    else:
        bot.reply_to(message, "🚫 **Comando solo disponible en chat privado para evitar la saturación del grupo.**")

if __name__ == "__main__":
    print("🚀 Sistema de procesamiento inmune activo...")
    bot.infinity_polling()
        
