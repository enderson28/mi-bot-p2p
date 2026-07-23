import os
import requests
import telebot
import time
import threading
from datetime import datetime
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from anuncios import iniciar_modulo_anuncios
from seguridad import validar_copia_pega, es_admin_vip, es_admin_especial, es_administrador
from seguridad import limpiar_comandos_chat
import re
import requests
from bs4 import BeautifulSoup

# ==========================================
# CONFIGURACIÓN Y VARIABLES GLOBALES
# ==========================================
TOKEN_TELEGRAM = os.getenv("TOKEN_TELEGRAM")
bot = telebot.TeleBot(TOKEN_TELEGRAM)

BOT_USERNAME = "BancoIDV_bot" # Reemplaza con el alias de tu bot sin el @

# CONFIGURACIÓN DE EXCLUSIVIDAD MULTI-CANAL
CANAL_PRUEBA = "@COMUNIDV"       # Canal de prueba
CANAL_CONGESTIONADO = "@COMUNIDADAS04" # Canal principal
CANAL_ADMINS = "@IDVADMINS"  # Reemplaza con el @ de tu grupo de admins
# USUARIOS AUTORIZADOS PARA EL COMANDO /bot
USUARIOS_AUTORIZADOS = ["@enderson28", "@AntonyS4", "@papitamaster"]

# CONFIGURACIÓN DE TIEMPOS
RATE_LIMIT_AVISO = 600       # 10 minutos para enfriamiento de avisos a usuarios
TIEMPO_VIDA_TABLA = 300      # 5 minutos para autodestrucción del monitor/intervención
grupos_tiempo_aviso = {}     # Registra cooldown por chat_id

# ==========================================
#  SISTEMA DE AUTODESTRUCCIÓN DE MENSAJES
# ==========================================
def borrar_mensaje_luego(chat_id, message_id, segundos):
    """Elimina un mensaje en segundo plano tras transcurrir los segundos indicados"""
    def eliminar():
        time.sleep(segundos)
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass # Ignora si el mensaje ya fue borrado manualmente
    
    threading.Thread(target=eliminar).start()

# ==========================================
#  CREACIÓN DE INTERFACES (BOTONES)
# ==========================================
def obtener_teclado_privado():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_precio = KeyboardButton("🟢 P2P~USDT 🟢")
    btn_intervencion = KeyboardButton("📊 Intervención 📊")
    btn_bpay = KeyboardButton("🔶 BPay 🔶")
    btn_gpay = KeyboardButton("🔵 GPay 🔵")
    
    markup.add(btn_precio, btn_intervencion)
    markup.add(btn_bpay, btn_gpay)
    return markup

def obtener_boton_actualizar_inline():
    markup = InlineKeyboardMarkup()
    btn_refresh = InlineKeyboardButton("🔄 Actualizar Tasas", callback_data="refrescar_tasas")
    markup.add(btn_refresh)
    return markup

# ==========================================
#  TEXTOS ORIGINALES COMPLETOS
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
    "3️⃣ Introduce los datos de tu tarjeta.\n"
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
    "• Provincial (BBVA): No cobra comisión, pero se recomienda dejar un margen fijo de 3$ a 5$ en la cuenta para evitar errores.\n\n"
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
    f"Al vender en VES, consulta mañana este bot. Usa solo los bolívares necesarios para volver a comprar tu capital base en el banco (<code>BCV + 0.5%</code>). <b>¡Deja tus ganancias acumuladas en USDT dentro de Binance como tu colchón de ahorro seguro!</b>"
)

# ==========================================
#  LÓGICA DE PROCESAMIENTO Y APIS
# ==========================================
def usuario_esta_unido(user_id):
    unido_prueba = False
    unido_congestionado = False

    try:
        m1 = bot.get_chat_member(CANAL_PRUEBA, user_id)
        if m1.status in ['creator', 'administrator', 'member']:
            unido_prueba = True
    except Exception:
        pass

    try:
        m2 = bot.get_chat_member(CANAL_CONGESTIONADO, user_id)
        if m2.status in ['creator', 'administrator', 'member']:
            unido_congestionado = True
    except Exception:
        pass

    return unido_prueba or unido_congestionado
    
    # Actualizacion de velocidad
def obtener_datos_bcv_validos():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    fecha_hoy_str = datetime.now().strftime("%Y-%m-%d")

    # --- INTENTO 1: DolarApi Ve (Obtiene Tasa y Fecha REAL del BCV) ---
    try:
        r = requests.get("https://ve.dolarapi.com/v1/dolares/oficial", timeout=2.0)
        if r.status_code == 200:
            datos = r.json()
            tasa = float(datos.get('promedio', 0))
            fecha_val = datos.get('fechaActualizacion', '')[:10]  # Formato AAAA-MM-DD
            
            # REGLA DE ORO: Tasa mayor a 0 Y fecha estrictamente igual a HOY
            if tasa > 0 and fecha_val == fecha_hoy_str:
                return tasa, fecha_val
    except Exception:
        pass

    # --- INTENTO 2: Scraping espejo BCV ---
    try:
        from bs4 import BeautifulSoup
        r = requests.get("https://ve.360data.cloud/bcv", headers=headers, timeout=2.0)
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, 'html.parser')
            elem_usd = soup.find('div', id='dolar') or soup.find('strong')
            if elem_usd:
                val_clean = elem_usd.text.strip().replace('.', '').replace(',', '.').strip()
                tasa = float(val_clean)
                if tasa > 0:
                    return tasa, fecha_hoy_str
    except Exception:
        pass

    # --- INTENTO 3: Fallback de Seguridad ---
    return 737.88, fecha_hoy_str
    
def obtener_tasa_binance_p2p(tipo_operacion, monto_bs):
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"

    headers = {
        "Accept": "*/*",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    payload = {
        "asset": "USDT",
        "fiat": "VES",
        "merchantCheck": True,
        "shieldMerchantUser": True,
        "page": 1,
        "rows": 10,  # Aumentamos a 10 para tener suficiente margen si hay varios restringidos
        "publisherType": "merchant",
        "tradeType": tipo_operacion.upper(),
        "transAmount": str(int(monto_bs))
    }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=3)
        if r.status_code == 200:
            datos = r.json().get('data', [])
            if datos:
                for elemento in datos:
                    adv = elemento.get('adv', {})
                    advertiser = elemento.get('advertiser', {})
                    
                    # 1. Validar que el anuncio esté activo y con precio
                    precio = adv.get('price')
                    
                    # 2. Validar que el comerciante NO tenga estado bloqueado/restringido
                    # Si 'userType' existe y el estado del usuario no es restringido
                    user_status = advertiser.get('userStatus', '')
                    
                    if precio and user_status != 'BLOCKED':
                        return float(precio)
    except Exception as e:
        print(f"⚠️ Error conectando con Binance P2P: {e}")

    return None

# ==========================================
#    CONSTRUCTORES DE MENSAJES (HTML)
# ==========================================
def construir_monitor_texto_html():
    tasa_bcv_cruda, fecha_valor_bcv = obtener_datos_bcv_validos()
    if not tasa_bcv_cruda:
        return "❌ Error temporal al conectar con la tasa base del BCV."

    tasa_bcv_ajustada = tasa_bcv_cruda * 1.005 # BCV + 0.5% (Intervención)

    # Definimos los 3 rangos con su nombre y el monto de USD de referencia
    rangos = [
        ("Rango Pequeño ($50 - $100)", 50.0),
        ("Rango Mediano ($100 - $300)", 150.0),
        ("Rango Mayor ($500+)", 500.0)
    ]

    texto = f"📊 <b>Monitor de Tasas Arbitraje P2P</b>\n"
    texto += f"📅 Vigencia BCV: <code>{fecha_valor_bcv}</code>\n"
    texto += f"🏛 BCV Oficial: <b>{tasa_bcv_cruda:.2f} Bs</b>\n"
    texto += f"⚙️ BCV + 0.5%: <b>{tasa_bcv_ajustada:.2f} Bs</b>\n"
    texto += f"🛡 <i>Filtros activos: Verificados | Comerciables 🟡🔻 | Pago: Todos ▼</i>\n"
    texto += "----------------------------------------\n\n"

    for nombre_rango, usd_ref in rangos:
        # Monto estimado en Bs para hacer la consulta del filtro en Binance
        monto_filtro_bs = usd_ref * tasa_bcv_ajustada

        # Obtenemos las tasas en tiempo real de Binance pasando el monto del filtro
        tasa_compra = obtener_tasa_binance_p2p("BUY", monto_filtro_bs)
        tasa_venta = obtener_tasa_binance_p2p("SELL", monto_filtro_bs)

        if tasa_compra and tasa_venta:
            filtro_bcv_bs = usd_ref * tasa_bcv_ajustada
            spread = tasa_venta - tasa_compra
            porcentaje_spread = (spread / tasa_compra) * 100

            texto += f"🔷 <b>{nombre_rango}</b>\n"
            texto += f"🟢 <b>Compra USDT:</b> <b>{tasa_compra:.2f} Bs</b>\n"
            texto += f"🔴 <b>Venta:</b> <b>{tasa_venta:.2f} Bs</b>\n"
            
            # Solo si es el Rango Mayor ($500+), insertamos el filtro justo debajo de 🔴 Venta
            if usd_ref == 500.0:
                texto += f"   └ 💡 <i>(Filtro base: ~{filtro_bcv_bs:,.0f} Bs)</i>\n"

            texto += f"📉 Spread: <b>{spread:.2f} Bs</b> (<b>{porcentaje_spread:.2f}%</b>)\n\n"
        else:
            texto += f"🔷 <b>{nombre_rango}</b>\n⚠️ <i>No se pudieron obtener tasas para este rango.</i>\n\n"

    #texto += "<i>Última actualización de tasas en vivo: Hace un instante.</i>"
    return texto
    
    
def construir_intervencion_texto_html(usuario=None):
    tasa_bcv_cruda, fecha_valor_bcv = obtener_datos_bcv_validos()
    if not tasa_bcv_cruda:
        return "❌ Error al obtener la tasa cambiaria de intervención."

    # Si es el admin especial, usa 1% (1.01). Si no, usa 0.5% (1.005)
    if usuario and es_admin_especial(usuario):
        porcentaje_txt = "1% Agregado"
        factor_multiplicador = 1.01
    else:
        porcentaje_txt = "0.5% Agregado"
        factor_multiplicador = 1.005

    tasa_intervencion = tasa_bcv_cruda * factor_multiplicador

    texto = (
        f"🚨 <b>¿Cuántos bolívares necesitas para comprar en Intervención?</b>\n"
        f"📅 <b>Fecha Valor BCV:</b> {fecha_valor_bcv}\n"
        f"🏛️ Tasa BCV Oficial: {tasa_bcv_cruda:.2f} Bs\n"
        f"💸 <b>Tasa Intervención: {tasa_intervencion:.2f} Bs</b> ({porcentaje_txt})\n"
        f"-----------------------------------\n"
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
        # 1. SI ES ADMINISTRADOR VIP
        if es_admin_vip(message.from_user):
            # Teclado ultralimpio para Administradores
            markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add(KeyboardButton("🟢 P2P-USDT 🟢"), KeyboardButton("📊 Intervención 📊"))
            
            texto_vip = (
                f"👋 <b>¡Hola, {message.from_user.first_name}!</b>\n\n"
                "Gracias por tu valiosa labor diaria manteniendo el orden en la comunidad - AntonyS4.\n"
                "🛡️ <i>Tienes activo el entorno VIP de trabajo rápido (sin distracciones ni guías de inicio).</i>"
            )
            bot.send_message(message.chat.id, texto_vip, parse_mode="HTML", reply_markup=markup)
            return

        # 2. SI ES USUARIO COMÚN (Mantiene verificación de canal y guías completas)
        if not usuario_esta_unido(message.from_user.id):
            texto_bloqueo = (
                "⚠️ <b>Acceso Restringido</b>\n\n"
                "Este bot es de uso exclusivo para nuestra comunidad.\n"
                "📢 <b>Únete a la comunidad oficial aquí:</b> @COMUNIDAS04\n\n"
                "<i>Una vez te hayas unido, vuelve a presionar /start.</i>"
            )
            bot.send_message(message.chat.id, texto_bloqueo, parse_mode="HTML")
            return

        # Mensaje recargado con teclado completo para novatos
        bot.send_message(message.chat.id, TEXTO_START, parse_mode="HTML", reply_markup=obtener_teclado_privado())
        

# Manejador para el botón P2P y el comando /precio
@bot.message_handler(commands=['precio', 'p2p'])
@bot.message_handler(func=lambda m: m.text and m.text.strip() == "🟢 P2P-USDT 🟢")
def handle_precio_comando(message):
    procesar_precio(message)

# Manejador para el botón de Intervención y el comando /intervencion
@bot.message_handler(commands=['intervencion'])
@bot.message_handler(func=lambda m: m.text and "Intervención" in m.text and m.text.strip().startswith("📊"))
def handle_intervencion_comando(message):
    procesar_intervencion(message)
    
@bot.message_handler(commands=['bpay', 'gpay'])
def handle_guias_comando(message):
    procesar_guias(message)
@bot.message_handler(commands=['bot'])
def handle_invitacion_comando(message):
    # 1. Borramos el comando /bot ejecutado inmediatamente
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

    # Identificador del usuario que escribió
    user_identifier = f"@{message.from_user.username}" if message.from_user.username else message.from_user.id

    # 2. Verificamos si es un usuario autorizado
    if user_identifier in USUARIOS_AUTORIZADOS or message.from_user.id in USUARIOS_AUTORIZADOS:
        
        texto_invitacion = (
            "🤖 <b>¡Aprovecha al máximo las herramientas del Bot!</b>\n\n"
            "Consulta en privado sin límites y sin esperar tiempos de enfriamiento:\n"
            "📊 Monitor P2P / BCV en tiempo real\n"
            "🧮 Calculadora de Intervención\n"
            "📜 Guías paso a paso\n\n"
            "👉 <b>Toca aquí para iniciar:</b> @BancoIDV_bot"
        )
        
        msg_inv = bot.send_message(message.chat.id, texto_invitacion, parse_mode="HTML")
        # El aviso de invitación se borra a los 3 minutos (180 seg) para no hacer basura
        borrar_mensaje_luego(message.chat.id, msg_inv.message_id, 180)

    else:
        # 3. Si no es autorizado (usuario normal u otro admin), desintegra el aviso en 5 segundos
        aviso = bot.send_message(
            message.chat.id, 
            f"⚠️ <b>Comando exclusivo del creador del bot</b> (@enderson28) (@AntonyS4) (@papitamaster).", 
            parse_mode="HTML"
        )
        borrar_mensaje_luego(message.chat.id, aviso.message_id, 5)
        
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
#  LÓGICA CON AUTODESTRUCCIÓN Y LIMPIEZA
# ==========================================
def procesar_precio(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    # --- 1. CHAT PRIVADO ---
    if message.chat.type == "private":
        if not usuario_esta_unido(user_id):
            bot.reply_to(message, "❌ No tienes acceso. Debes unirte al canal oficial para usar el bot.")
            return

        try:
            # 1. Armamos el monitor base
            monitor_base = construir_monitor_texto_html()

            # 2. Si es Admin VIP, mostramos SOLO el monitor (ultralimpio)
            # Si es usuario común, le pegamos la Regla de Oro abajo
            if es_admin_vip(message.from_user):
                texto_completo = monitor_base
            else:
                texto_completo = monitor_base + TEXTO_REGLA_ORO_HTML

            # 3. Enviamos el mensaje correspondiente
            bot.send_message(chat_id, texto_completo, parse_mode="HTML", reply_markup=obtener_boton_actualizar_inline())

        except Exception as e:
            print(f"Error en precio privado: {e}")
            bot.reply_to(message, "❌ Error al generar la consulta privada.")
        return
        

    # --- 2. EN GRUPOS ---
    # A) Borramos inmediatamente el mensaje del comando ejecutado (sea Admin o Usuario)
    try:
        bot.delete_message(chat_id, message.message_id)
    except Exception:
        pass
    if es_administrador(bot, chat_id, user_id, message.from_user):
        try:
            # B) Por defecto NO hay botones para evitar spam en grupos públicos
            markup_precio = None

            # Si estamos en el grupo de admins, creamos los botones
            if chat_id == CANAL_ADMINS or (message.chat.username and f"@{message.chat.username.lower()}" == CANAL_ADMINS.lower()):
                markup_precio = InlineKeyboardMarkup()
                markup_precio.row(
                    InlineKeyboardButton("🔄 Actualizar Tasas", callback_data="refrescar_tasas"),
                    InlineKeyboardButton("🗑️ Borrar", callback_data="borrar_tabla_admin")
                )

            # Enviamos el mensaje (saldrá con botones en VIP, y limpio en grupos públicos)
            msg_enviado = bot.send_message(
                chat_id,
                construir_monitor_texto_html(),
                parse_mode="HTML",
                reply_markup=markup_precio
            )

            # C) Autodestruimos la lista de precios tras 5 minutos
            borrar_mensaje_luego(chat_id, msg_enviado.message_id, TIEMPO_VIDA_TABLA)

        except Exception:
            pass


    else:

        # SI ES USUARIO COMÚN:
        ahora = time.time()
        ultima_vez_aviso = grupos_tiempo_aviso.get(chat_id, 0)
        
        if ahora - ultima_vez_aviso > RATE_LIMIT_AVISO:
            try:
                aviso = bot.send_message(
                    chat_id, 
                    f"❌ <b>Comando exclusivo para Administradores.</b>\n\n"
                    f"Hola @{message.from_user.username or message.from_user.first_name}. Para mantener el orden, este comando está restringido en el grupo.\n"
                    f"👉 Consulta todas las tasas libremente en mi chat privado: @{BOT_USERNAME}",
                    parse_mode="HTML"
                )
                grupos_tiempo_aviso[chat_id] = ahora
                # Autodestruimos el aviso tras 10 segundos
                borrar_mensaje_luego(chat_id, aviso.message_id, 10)
            except Exception:
                pass

def procesar_intervencion(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    # --- 1. CHAT PRIVADO ---
    if message.chat.type == "private":
        if not usuario_esta_unido(user_id):
            bot.reply_to(message, "❌ No tienes acceso. Debes unirte al canal oficial para usar el bot.")
            return

        # Creamos el botón flotante para actualizar
        markup_intervencion = InlineKeyboardMarkup()
        markup_intervencion.add(InlineKeyboardButton("🔄 Actualizar Cálculo", callback_data="refrescar_intervencion"))

        bot.send_message(
            chat_id, 
            construir_intervencion_texto_html(), 
            parse_mode="HTML",
            reply_markup=markup_intervencion
        )
        return

      # --- 2. EN GRUPOS ---
    try:
        bot.delete_message(chat_id, message.message_id)
    except Exception:
        pass

    if es_administrador(bot, chat_id, user_id, message.from_user):
        try:
            # 2. SOLO si estamos en el grupo de admins, creamos los 2 botones VIP
            if chat_id == CANAL_ADMINS or (message.chat.username and f"@{message.chat.username.lower()}" == CANAL_ADMINS.lower()):
                markup_intervencion = InlineKeyboardMarkup()
                markup_intervencion.row(
                    InlineKeyboardButton("🔄 Actualizar Cálculo", callback_data="refrescar_intervencion"),
                    InlineKeyboardButton("🗑️ Borrar", callback_data="borrar_tabla_admin")
                )
            else:
                markup_intervencion = None
    
            # 3. ENVIAMOS EL MENSAJE (Se envía en TODOS los grupos donde seas Admin/Propietario)
            msg_enviado = bot.send_message(
                chat_id,
                construir_intervencion_texto_html(),
                parse_mode="HTML",
                reply_markup=markup_intervencion  # Será None en los grupos normales, y con botones en Admin
            )

              # 4. Autodestrucción del mensaje
            borrar_mensaje_luego(chat_id, msg_enviado.message_id, TIEMPO_VIDA_TABLA)

        except Exception:
            pass
    else:
          # Si un usuario común intenta usarlo en el grupo, aplica el Rate Limit de aviso
        ahora = time.time()
        ultima_vez_aviso = grupos_tiempo_aviso.get(chat_id, 0)

        if ahora - ultima_vez_aviso > RATE_LIMIT_AVISO:
            try:
                aviso = bot.send_message(
                    chat_id,
                    f"❌ <b>Comando exclusivo para Administradores.</b>\n\n"
                    f"Hola @{message.from_user.username or message.from_user.first_name}. Para mantener el orden, este bot es de uso exclusivo de los administradores.\n"
                    f"👉 Consulta todas las tasas libremente en mi chat privado: @{BOT_USERNAME}",
                    parse_mode="HTML"
                )
                grupos_tiempo_aviso[chat_id] = ahora
                borrar_mensaje_luego(chat_id, aviso.message_id, 10)
            except Exception:
                pass
                
def procesar_guias(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    texto = message.text.lower().strip()
    es_bpay = texto in ['bpay', '/bpay', '!bpay'] or texto.startswith('/bpay')

    # --- 1. CHAT PRIVADO ---
    if message.chat.type == "private":
        if not usuario_esta_unido(user_id):
            bot.reply_to(message, "❌ No tienes acceso. Debes unirte al canal oficial para usar el bot.")
            return
            
        if es_bpay:
            bot.reply_to(message, TEXTO_BPAY, parse_mode="HTML")
        else:
            bot.reply_to(message, TEXTO_GPAY, parse_mode="HTML")
        return  # 👈 Este return corta la función AQUÍ si es privado

    # --- 2. EN GRUPOS (SILENCIO ABSOLUTO Y BORRADO AUTOMÁTICO) ---
    # Se ejecuta solo si el mensaje NO es privado.
    try:
        bot.delete_message(chat_id, message.message_id)
    except Exception:
        pass
        
        

# ==========================================
#    MANEJADOR DEL BOTÓN INLINE (REFRESCAR)
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data == "refrescar_tasas")
def callback_refrescar_tasas(call):
    if not usuario_esta_unido(call.from_user.id):
        bot.answer_callback_query(call.id, text="❌ Acceso denegado. No perteneces al canal.")
        return

    try:
        monitor_fresco = construir_monitor_texto_html()

        if es_admin_vip(call.from_user):
            texto_editado = monitor_fresco + f"\n\n<i>Última actualización de tasas en vivo: Hace un instante.</i>"
        else:
            texto_editado = monitor_fresco + TEXTO_REGLA_ORO_HTML + f"\n\n<i>Última actualización de tasas en vivo: Hace un instante.</i>"

        # Construimos el teclado evaluando si está en el grupo de admins
        markup_tasas = InlineKeyboardMarkup()
        if call.message.chat.id == CANAL_ADMINS or es_admin_vip(call.from_user):
            markup_tasas.row(
                InlineKeyboardButton("🔄 Actualizar Tasas", callback_data="refrescar_tasas"),
                InlineKeyboardButton("🗑️ Borrar", callback_data="borrar_mensaje")
            )
        else:
            markup_tasas.add(InlineKeyboardButton("🔄 Actualizar Tasas", callback_data="refrescar_tasas"))

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=texto_editado,
            parse_mode="HTML",
            reply_markup=markup_tasas
        )
        bot.answer_callback_query(call.id, text="¡Monitor de Arbitraje actualizado! ⚡")
    except Exception:
        bot.answer_callback_query(call.id, text="Las tasas en Binance siguen siendo las mismas.")

# ==========================================
# BOTÓN FLOTANTE PARA REFRESCAR INTERVENCIÓN
# ==========================================

@bot.callback_query_handler(func=lambda call: call.data == "refrescar_intervencion")
def callback_refrescar_intervencion(call):
    if not usuario_esta_unido(call.from_user.id):
        bot.answer_callback_query(call.id, text="❌ Acceso denegado. No perteneces al canal.")
        return

    try:
        texto_fresco = construir_intervencion_texto_html(call.from_user)

        # Construimos el teclado evaluando si está en el grupo de admins
        markup_intervencion = InlineKeyboardMarkup()
        if call.message.chat.id == CANAL_ADMINS or es_admin_vip(call.from_user):
            markup_intervencion.row(
                InlineKeyboardButton("🔄 Actualizar Cálculo", callback_data="refrescar_intervencion"),
                InlineKeyboardButton("🗑️ Borrar", callback_data="borrar_mensaje")
            )
        else:
            markup_intervencion.add(InlineKeyboardButton("🔄 Actualizar Cálculo", callback_data="refrescar_intervencion"))

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=texto_fresco,
            parse_mode="HTML",
            reply_markup=markup_intervencion
        )
        bot.answer_callback_query(call.id, text="¡Tabla de Intervención actualizada! 📊")
    except Exception:
        bot.answer_callback_query(call.id, text="Las tasas se mantienen actualizadas. 🏦")
                    
    # ============================================
# BOTÓN FLOTANTE PARA BORRAR (PRECIO E INTERVENCIÓN)
# ============================================
@bot.callback_query_handler(func=lambda call: call.data == "borrar_mensaje")
def callback_borrar_tabla_admin(call):
    # 1. Verifica si quien presiona es Administrador o VIP
    if not es_administrador(bot, call.message.chat.id, call.from_user.id, call.from_user):
        bot.answer_callback_query(
            call.id, 
            text="❌ Solo los administradores pueden eliminar esta tabla.", 
            show_alert=True
        )
        return

    # 2. Borra la tabla al instante (sea de precio o intervención)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        bot.answer_callback_query(
            call.id, 
            text="⚠️ No se pudo eliminar el mensaje o ya fue borrado."
        )      
# ==========================================
#     FILTRO DE SEGURIDAD GENERAL (ABAJO)
# ==========================================

@bot.message_handler(func=lambda m: m.chat.type != "private", content_types=['text'])
def filtro_seguridad_chat(message):
    # 1. Borra comandos no deseados (/ban, /sexo, etc.)
    if limpiar_comandos_chat(bot, message):
        return
        
    es_admin = es_administrador(bot, message.chat.id, message.from_user.id, message.from_user)
    
    # Si un usuario común pegó un reporte oficial, lo borra y se detiene
    if validar_copia_pega(bot, message, es_admin):
        return
# ==========================================
#            EJECUCIÓN DEL BOT
# ==========================================

if __name__ == "__main__":
    iniciar_modulo_anuncios(bot)
    print("🚀 Bot Maestro en línea con limpieza automática y temporizador de 5 min...")
    bot.infinity_polling()
