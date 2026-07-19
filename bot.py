import requests
import telebot
import time
from datetime import datetime
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ==========================================
# CONFIGURACIÓN Y TOKEN
# ==========================================
TOKEN_TELEGRAM = "8632019517:AAHEegmOwcC35emzY5q75o6NUbs704cMD6g"
bot = telebot.TeleBot(TOKEN_TELEGRAM)

BOT_USERNAME = "BancoIDV_bot" 

# CONFIGURACIÓN DE TIEMPOS (COOLDOWN)
RATE_LIMIT = 900  # 15 minutos en segundos para usuarios comunes en el grupo
usuarios_tiempo = {} 

# ==========================================
#  CREACIÓN DE INTERFACES (BOTONES)
# ==========================================
def obtener_teclado_privado():
    """Genera el menú de botones inferiores para el chat privado"""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_precio = KeyboardButton("🟢 P2P~USDT 🟢")
    btn_intervencion = KeyboardButton("📊 Intervención 📊")
    btn_bpay = KeyboardButton("🔶 BPay 🔶")
    btn_gpay = KeyboardButton("🔵 GPay 🔵")
    
    markup.add(btn_precio, btn_intervencion)
    markup.add(btn_bpay, btn_gpay)
    return markup

def obtener_boton_actualizar_inline():
    """Genera el botón flotante debajo del mensaje para refrescar tasas"""
    markup = InlineKeyboardMarkup()
    btn_refresh = InlineKeyboardButton("🔄 Actualizar Tasas", callback_data="refrescar_tasas")
    markup.add(btn_refresh)
    return markup

# ==========================================
#  TEXTOS ORIGINALES EXTRAÍDOS DE CAPTURAS
# ==========================================
TEXTO_START = (
    "👋 <b>¡Bienvenido al Monitor Oficial IDV ~ Arbitraje P2P!</b>\n\n"
    "Este bot es tu herramienta aliada para proteger tu capital y generar ganancias reales en Venezuela 🇻🇪. Aquí no tienes que adivinar; el sistema calcula todo por ti.\n\n"
    "🚀 <b>¿Cómo empezar? Usa el menú interactivo de botones aquí abajo o escribe los comandos:</b>\n"
    "🔹 <code>/precio</code> o botón <b>P2P~USDT</b> — Muestra las tasas reales BCV, precios P2P y la regla de oro.\n"
    "🔹 <code>/intervencion</code> o botón <b>Intervención</b> — Desglose de bolívares requeridos para la compra de dólares oficiales.\n"
    "🔹 <code>/bpay</code> o botón <b>BPay</b> — Guía paso a paso para cargar USD bancarios a Binance.\n"
    "🔹 <code>/gpay</code> o botón <b>GPay</b> — Ruta alternativa para Deposito USD usando Google Pay.\n\n"
    "💡 <b>Nota:</b> <i>Si eres nuevo, lee con atención la 'Regla de Oro' al final del monitor de precios. ¡Evita comprar costoso en el P2P!</i>"
)

TEXTO_BPAY = (
    "💳 <b>Estrategia BPay: Carga de USD Bancarios a Binance</b>\n\n"
    "Este método te permite meter tus USD de intervención del banco nacional a la plataforma para generar ganancias en USDT:\n\n"
    "⚠️ <b>Costos Fijos:</b> Comisión de 3.6% a 4.1% por depósito con tarjetas nacionales en moneda extranjera.\n\n"
    "📌 <b>Pasos para la Operación:</b>\n"
    "1️⃣ Adquiere tus dólares por intervención en tu banco nacional (BDV, Provincial, Banesco, etc.).\n"
    "2️⃣ Ve a la plataforma, selecciona la opción de Depósito en USD (Fiat) mediante tarjeta de crédito o débito.\n"
    "3️⃣ Introduce los datos de tu tarjeta.\n\n"
    "🚨 <b>PUNTO CLAVE (Evita Bloqueos):</b> El banco nacional deduce una comisión interna que Binance NO calcula en su pantalla. Para evitar que el banco rechace la operación por fondos insuficientes y bloquee tu tarjeta, debes restar estos porcentajes al saldo total de tu cuenta antes de colocar el monto en BPay:\n"
    "• BDV MasterCard (Maestro): Restar 1.5%\n"
    "• BDV Tarjeta Internacional: Restar 2.5%\n"
    "• Banco del Tesoro: Restar 2.5%\n"
    "• Provincial (BBVA): No cobra comisión, se recomienda dejar un margen fijo de 3$ a 5$ en la cuenta USD para evitar errores.\n\n"
    "👉 <i>Coloca en BPay únicamente el resultado neto de esa resta.</i>\n\n"
    "4️⃣ Con tus USD Fiat ya disponibles, realiza el intercambio desde trade (convertir) a USDT.\n\n"
    "🔥 <b>Finalidad:</b> Al tener tus USDT, usa nuestro comando <code>/precio</code> para evaluar la tasa de venta actual en el P2P y liquidar en bolívares, asegurando tu margen de ganancia sobre la tasa base del BCV."
)

TEXTO_GPAY = (
    "📱 <b>Estrategia GPay: Carga de USD Bancarios a Binance</b>\n\n"
    "Una ruta alternativa y rápida utilizando la pasarela de Google para procesar tus dólares de intervención:\n\n"
    "⚠️ <b>Costos Fijos:</b> Comisión fija del 4.1% por el procesamiento del método.\n\n"
    "📌 <b>Pasos para la Operación:</b>\n"
    "1️⃣ Compra tus USD oficiales en la banca nacional a tasa de intervención del BCV.\n"
    "2️⃣ Vincula la tarjeta internacional/nacional en divisas de tu banco a tu billetera de Google Pay (GPay).\n"
    "3️⃣ En la plataforma, selecciona la opción de Depósito USD utilizando GPay como procesador instantáneo.\n\n"
    "🚨 <b>PUNTO CLAVE (Evita Bloqueos):</b> El banco nacional deduce una comisión interna que Binance NO calcula en su pantalla. Para evitar que el banco rechace la operación por fondos insuficientes y bloquee tu tarjeta, debes restar estos porcentajes al saldo total de tu cuenta antes de colocar el monto en GPay:\n"
    "• BDV MasterCard (Maestro): Restar 1.5%\n"
    "• BDV Tarjeta Internacional: Restar 2.5%\n"
    "• Banco del Tesoro: Restar 2.5%\n"
    "• Provincial (BBVA): No cobra comisión, se recomienda dejar un margen fijo de 3$ a 5$ en la cuenta USD para evitar errores de Fondos.\n\n"
    "👉 <i>Coloca en GPay únicamente el resultado neto de esa resta.</i>\n\n"
    "4️⃣ Con los USD Fiat ya disponibles, realiza el intercambio desde trade (convertir) a USDT.\n\n"
    "🔥 <b>Finalidad:</b> Saltarse el P2P de compra para obtener el USDT mucho más económico. El beneficio real se consolida al vender esos USDT en el P2P de salida utilizando los precios verificados que te da el comando <code>/precio</code>."
)

TEXTO_REGLA_ORO_HTML = (
    f"\n----------------------------------------\n"
    f"💡 <b>REGLA DE ORO PARA GENERAR GANANCIAS</b>\n\n"
    f"⚠️ <b>¿Quieres comerciar? No compres USDT en el P2P:</b>\n"
    f"Usar la opción de <code>🟢 Compra P2P</code> reduce casi a cero tu margen de ganancia comercial. El verdadero beneficio se obtiene haciendo la ruta institucional.\n\n"
    f"📌 <b>Excepción (Uso como Ahorro):</b>\n"
    f"Si deseas comprar USDT por el arbitraje de <code>🟢 Compra</code>, también es perfectamente viable teniendo en cuenta que será una inversión estable sin margen de ganancias al momento (un tipo de ahorro), porque no estás comprando al USDT oficial sino al paralelo de arbitraje.\n\n"
    f"🔄 <b>La Ruta para Arbitraje Activo:</b>\n"
    f"1️⃣ Adquiere USD oficiales en tu banco a tasa BCV.\n"
    f"2️⃣ Pásalos a Binance mediante /bpay o /gpay (Depósito USD).\n"
    f"3️⃣ Convierte a USDT y vende usando la tasa de <code>🔴 Venta</code> de este monitor.\n\n"
    f"🛡️ <b>Estrategia de Capital Seguro:</b>\n"
    f"Al vender en Bs, consulta mañana este bot. Usa solo los bolívares necesarios para volver a comprar tu capital base en el banco (<code>BCV + 0.5%</code>). <b>¡Deja tus ganancias acumuladas en USDT dentro de Binance como tu colchón de ahorro seguro!</b>"
)

# ==========================================
#          LÓGICA DE CÁLCULOS Y APIS
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
        except Exception:
            return None

def obtener_tasa_binance_p2p(tipo_operacion, monto_ves_filtro):
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    payload = {
        "asset": "USDT", "fiat": "VES", "merchantCheck": False, "page": 1,
        "payTypes": [], "publisherType": "merchant", "rows": 1,
        "tradeType": "BUY" if tipo_operacion.lower() == "compra" else "SELL",
        "transAmount": str(int(monto_ves_filtro))
    }
    try:
        res = requests.post(url, json=payload, timeout=8)
        data = res.json()
        if data and "data" in data and len(data["data"]) > 0:
            return float(data["data"][0]["adv"]["price"])
    except Exception:
        pass
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

# ==========================================
#    CONSTRUCTORES DE MENSAJES (HTML)
# ==========================================
def construir_monitor_texto_html():
    tasa_bcv_cruda = obtener_tasa_bcv_real()
    if not tasa_bcv_cruda:
        return "❌ Error temporal al conectar con la tasa base."

    tasa_bcv_ajustada = tasa_bcv_cruda * 1.005
    rangos = [("Pequeño ($50 - $100)", 50.0), ("Mediano ($100 - $300)", 150.0), ("Mayor ($500+)", 500.0)]
    
    texto = (
        f"📊 <b>Monitor de Tasas Arbitraje P2P</b>\n"
        f"🏛️ BCV Oficial: {tasa_bcv_cruda:.2f} Bs\n"
        f"⚙️ BCV + 0.5%: {tasa_bcv_ajustada:.2f} Bs\n"
        f"🛡️ <i>Filtros activos: Solo Anunciantes Verificados</i>\n"
        f"----------------------------------------\n\n"
    )
    for nombre, factor in rangos:
        filtro = factor * tasa_bcv_ajustada
        c = obtener_tasa_binance_p2p("compra", filtro)
        v = obtener_tasa_binance_p2p("venta", filtro)
        if c and v:
            s = v - c
            p = (s / c) * 100
            texto += f"🔹 <b>Rango {nombre}</b>\n🟢 Compra: {c:.2f} Bs | 🔴 Venta: {v:.2f} Bs\n📉 Spread: {s:.2f} Bs ({p:.2f}%)\n\n"
        else:
            texto += f"🔹 <b>Rango {nombre}:</b> <i>Sin anunciantes</i>\n\n"
    return texto

def construir_intervencion_texto_html():
    tasa_bcv_cruda = obtener_tasa_bcv_real()
    if not tasa_bcv_cruda:
        return "❌ Error al obtener la tasa cambiaria de intervención."
        
    tasa_intervencion = tasa_bcv_cruda * 1.005
    fecha_hoy = datetime.now().strftime("%d/%m/%Y")
    
    texto = (
        f"🚨 <b>¿Cuántos bolívares necesitas para comprar en Intervención?</b>\n\n"
        f"📅 <b>Fecha:</b> {fecha_hoy}\n\n"
        f"🏛️ Tasa BCV Hoy: {tasa_bcv_cruda:.2f} Bs\n"
        f"💸 <b>Tasa Intervención: {tasa_intervencion:.2f} Bs</b> (0.5% Agregado)\n"
        f"----------------------------------------\n"
    )
    
    for usd in range(100, 1100, 100):
        total_ves = usd * tasa_intervencion
        texto += f"💵 {usd:,} USD  ➡️  <b>Bs. {total_ves:,.2f}</b>\n"
        
    return texto

# ==========================================
#     MANEJADORES DE COMANDOS Y BOTONES
# ==========================================
@bot.message_handler(commands=['start'])
def handle_start(message):
    if message.chat.type == "private":
        bot.send_message(message.chat.id, TEXTO_START, parse_mode="HTML", reply_markup=obtener_teclado_privado())

@bot.message_handler(commands=['precio'])
def handle_precio_comando(message):
    procesar_precio(message)

@bot.message_handler(commands=['intervencion'])
def handle_intervencion_comando(message):
    procesar_intervencion(message)

@bot.message_handler(commands=['bpay', 'gpay'])
def handle_guias_comando(message):
    procesar_guias(message)

@bot.message_handler(func=lambda message: message.text in ["🟢 P2P~USDT 🟢", "📊 Intervención 📊", "🔶 BPay 🔶", "🔵 GPay 🔵"])
def handle_botones_menu(message):
    if message.chat.type == "private":
        if message.text == "🟢 P2P~USDT 🟢":
            procesar_precio(message)
        elif message.text == "📊 Intervención 📊":
            procesar_intervencion(message)
        elif message.text in ["🔶 BPay 🔶", "🔵 GPay 🔵"]:
            procesar_guias(message)

# ==========================================
#     LÓGICA INTERNA DE EJECUCIÓN
# ==========================================
def procesar_precio(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # --- CHAT PRIVADO ---
    if message.chat.type == "private":
        try:
            monitor_base = construir_monitor_texto_html()
            texto_completo = monitor_base + TEXTO_REGLA_ORO_HTML
            # Se envía el monitor de precios junto con su botón inline de actualizar
            bot.send_message(chat_id, texto_completo, parse_mode="HTML", reply_markup=obtener_boton_actualizar_inline())
        except Exception as e:
            print(f"Error en precio privado: {e}")
            bot.reply_to(message, "❌ Error al generar la consulta privada.")
        return

    # --- EN GRUPOS ---
    if es_administrador(chat_id, user_id):
        try:
            bot.reply_to(message, construir_monitor_texto_html(), parse_mode="HTML")
        except Exception:
            bot.reply_to(message, "❌ Error en consulta de administrador.")
    else:
        ahora = time.time()
        ultima_vez = usuarios_tiempo.get(user_id, 0)
        
        if ahora - ultima_vez < RATE_LIMIT:
            espera_minutos = int((RATE_LIMIT - (ahora - ultima_vez)) // 60)
            espera_segundos = int((RATE_LIMIT - (ahora - ultima_vez)) % 60)
            bot.reply_to(
                message, 
                f"⏳ <b>Modo ahorro de chat:</b> Este comando tiene un reposo de 15 minutos para evitar la saturación.\n"
                f"Por favor espera <b>{espera_minutos}m {espera_segundos}s</b> o consulta directamente en mi chat privado sin restricciones de tiempo.", 
                parse_mode="HTML"
            )
        else:
            try:
                monitor_html = construir_monitor_texto_html()
                texto_grupo_usuario = monitor_html + (
                    f"\n----------------------------------------\n"
                    f"💡 <b>¿Eres nuevo en el arbitraje?</b>\n"
                    f"Para conocer la <b>Regla de Oro</b> y aprender a generar ganancias reales, consulta este comando en mi chat privado: @{BOT_USERNAME}"
                )
                bot.reply_to(message, texto_grupo_usuario, parse_mode="HTML")
                usuarios_tiempo[user_id] = ahora
            except Exception:
                bot.reply_to(message, "⚠️ Inconveniente temporal al procesar los datos.")

def procesar_intervencion(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # --- CHAT PRIVADO ---
    if message.chat.type == "private":
        bot.send_message(chat_id, construir_intervencion_texto_html(), parse_mode="HTML")
        return
        
    # --- EN GRUPOS ---
    if es_administrador(chat_id, user_id):
        bot.reply_to(message, construir_intervencion_texto_html(), parse_mode="HTML")
    else:
        pass # Silencio absoluto para usuarios normales en grupos

def procesar_guias(message):
    if message.chat.type == "private":
        if 'bpay' in message.text.lower() or '🔶 bpay 🔶' in message.text:
            bot.reply_to(message, TEXTO_BPAY, parse_mode="HTML")
        else:
            bot.reply_to(message, TEXTO_GPAY, parse_mode="HTML")
    else:
        pass # Silencio absoluto en grupos para comandos /bpay o /gpay

# ==========================================
#    MANEJADOR DEL BOTÓN INLINE (REFRESCAR)
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data == "refrescar_tasas")
def callback_refrescar_tasas(call):
    try:
        monitor_fresco = construir_monitor_texto_html()
        texto_editado = monitor_fresco + TEXTO_REGLA_ORO_HTML + f"\n\n🔄 <i>Última actualización de tasas en vivo: Hace un instante.</i>"
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=texto_editado,
            parse_mode="HTML",
            reply_markup=obtener_boton_actualizar_inline()
        )
        bot.answer_callback_query(call.id, text="¡Monitor de Arbitraje actualizado! ⚡")
    except Exception:
        bot.answer_callback_query(call.id, text="Las tasas en Binance siguen siendo las mismas. 💸")

if __name__ == "__main__":
    print("🚀 Bot con botón de intervención privado e inline dinámico activo...")
    bot.infinity_polling()
            
