import requests
import telebot
import time
import threading
from datetime import datetime
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from anuncios import iniciar_modulo_anuncios
from seguridad import validar_copia_pega, es_admin_vip, es_admin_especial
import re
import requests
from bs4 import BeautifulSoup

# ==========================================
# CONFIGURACIÓN Y VARIABLES GLOBALES
# ==========================================
TOKEN_TELEGRAM = "8632019517:AAHEegmOwcC35emzY5q75o6NUbs704cMD6g"
bot = telebot.TeleBot(TOKEN_TELEGRAM)

BOT_USERNAME = "BancoIDV_bot" # Reemplaza con el alias de tu bot sin el @

# CONFIGURACIÓN DE EXCLUSIVIDAD MULTI-CANAL
CANAL_PRUEBA = "@COMUNIDV"       # Canal de prueba
CANAL_CONGESTIONADO = "@COMUNIDADAS04" # Canal principal
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
    

def obtener_datos_bcv_validos():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    
    # --- INTENTO 1: Scraping Directo al BCV ---
    try:
        url = "https://www.bcv.org.ve/"
        response = requests.get(url, headers=headers, timeout=6, verify=False)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            usd_div = soup.find('div', id='dolar')
            if usd_div:
                texto_raw = usd_div.find('strong').text.strip()
                # Extrae solo números y comas/puntos (ej: "737,23210000" -> 737.23)
                monto_limpio = re.search(r'[\d.,]+', texto_raw)
                if monto_limpio:
                    val_str = monto_limpio.group(0).replace('.', '').replace(',', '.')
                    tasa = round(float(val_str), 2)
                    
                    fecha_span = soup.find('span', class_='date-display-single')
                    fecha_val = fecha_span.text.strip() if fecha_span else "En Vivo"
                    
                    return tasa, fecha_val
    except Exception as e:
        print(f"⚠️ Falló scraping directo del BCV: {e}")

    # --- INTENTO 2: Respaldo DolarApi ---
    try:
        url_respaldo = "https://ve.dolarapi.com/v1/dolares/oficial"
        r = requests.get(url_respaldo, timeout=5)
        if r.status_code == 200:
            datos = r.json()
            tasa = float(datos.get('promedio', 0))
            fecha_val = datos.get('fechaActualizacion', 'En Vivo')[:10]
            return tasa, fecha_val
    except Exception as e:
        print(f"⚠️ Falló la API de respaldo: {e}")

    return None, None
    
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
    tasa_bcv_cruda, fecha_valor_bcv = obtener_datos_bcv_validos()
    if not tasa_bcv_cruda:
        return "❌ Error temporal al conectar con la tasa base del BCV."

    tasa_bcv_ajustada = tasa_bcv_cruda * 1.005
    rangos = [("Pequeño ($50 - $100)", 50.0), ("Mediano ($100 - $300)", 150.0)]

    texto = (
        f"📊 <b>Monitor de Tasas Arbitraje P2P</b>\n"
        f"📅 <b>Vigencia BCV:</b> {fecha_valor_bcv}\n"
        f"🏛️ BCV Oficial: {tasa_bcv_cruda:.2f} Bs\n"
        f"⚙️ BCV + 0.5%: {tasa_bcv_ajustada:.2f} Bs\n"
        f"🛡️ <i>Filtros activos: Solo Anunciantes Verificados</i>\n"
        f"----------------------------------------\n"
    )

    for nombre, factor in rangos:
        filtro = factor * tasa_bcv_ajustada

        try:
            c = obtener_tasa_binance_p2p(filtro, "BUY")
            v = obtener_tasa_binance_p2p(filtro, "SELL")
        except Exception as e:
            print(f"⚠️ Error al consultar Binance P2P: {e}")
            c, v = None, None

        if c and v:
            s = v - c
            p = (s / c) * 100
            texto += f"• <b>Rango {nombre}:</b>\n🟢 Compra: {c:.2f} Bs | 🔴 Venta: {v:.2f} Bs\n"
        else:
            texto += f"• <b>Rango {nombre}:</b> <i>Cargando anunciantes Binance...</i>\n"

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
                "Gracias por tu valiosa labor diaria manteniendo el orden en la comunidad.\n"
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
        

@bot.message_handler(commands=['precio'])
def handle_precio_comando(message):
    procesar_precio(message)

@bot.message_handler(commands=['intervencion'])
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

    if es_administrador(chat_id, user_id):
        try:
            # B) Enviamos el monitor
            msg_enviado = bot.send_message(chat_id, construir_monitor_texto_html(), parse_mode="HTML")
            # C) Autodestruimos la lista de precios tras 5 minutos (300 segundos)
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
        bot.send_message(chat_id, construir_intervencion_texto_html(message.from_user), parse_mode="HTML")
        return
        
    # --- 2. EN GRUPOS ---
    # A) Borramos inmediatamente el mensaje del comando ejecutado (sea Admin o Usuario)
    try:
        bot.delete_message(chat_id, message.message_id)
    except Exception:
        pass

    if es_administrador(chat_id, user_id):
        try:
            # B) Enviamos la tabla de intervención
            msg_enviado = bot.send_message(chat_id, construir_intervencion_texto_html(), parse_mode="HTML")
            # C) Autodestruimos la tabla tras 5 minutos (300 segundos)
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
                    f"👉 Consulta la calculadora de intervención libremente en mi chat privado: @{BOT_USERNAME}",
                    parse_mode="HTML"
                )
                grupos_tiempo_aviso[chat_id] = ahora
                # Autodestruimos el aviso tras 10 segundos
                borrar_mensaje_luego(chat_id, aviso.message_id, 10)
            except Exception:
                pass

def procesar_guias(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    es_bpay = 'bpay' in message.text.lower() or '🔶 bpay 🔶' in message.text

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
        bot.answer_callback_query(call.id, text="❌ Acceso denegado. No perteneces al canal.", show_alert=True)
        return

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

# ==========================================
#     FILTRO DE SEGURIDAD GENERAL (ABAJO)
# ==========================================

@bot.message_handler(func=lambda m: m.chat.type != "private", content_types=['text'])
def filtro_seguridad_chat(message):
    es_admin = es_administrador(message.chat.id, message.from_user.id)
    
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
