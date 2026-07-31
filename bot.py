import http.server
import socketserver
import os
import json
import requests
import telebot
import time
import threading
from datetime import datetime, timedelta
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from anuncios import iniciar_modulo_anuncios
from seguridad import validar_copia_pega, es_admin_vip, es_admin_especial, es_administrador, es_chat_permitido
from seguridad import limpiar_comandos_chat
import re
import urllib3
from bs4 import BeautifulSoup
# Desactivar avisos de certificados SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
USUARIOS_AUTORIZADOS = [5073264705, "@AntonyS4", "@papitamaster"]
# Creador Supremo (Tu ID numérico real)
CREADOR_ID = 5073264705  # Reemplaza por tu ID numérico

# Lista unificada de chats donde el bot responderá a los demás
CHATS_PERMITIDOS = [CANAL_PRUEBA, CANAL_CONGESTIONADO, CANAL_ADMINS]
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
    btn_precio = KeyboardButton("🟢 P2P~USDT 🔴")
    btn_intervencion = KeyboardButton("📊 Intervencion 📊")
    btn_regla = KeyboardButton("📜 Regla de Oro 📜")
    btn_bpay = KeyboardButton("🔶 BPay 🔶")
    btn_gpay = KeyboardButton("🔵 GPay 🔵")
    btn_soporte = KeyboardButton("⚙️ Soporte")  # <-- Botón nuevo

    markup.add(btn_precio, btn_intervencion)
    markup.add(btn_regla)
    markup.add(btn_bpay, btn_gpay)
    markup.add(btn_soporte)  # <-- Ocupará la fila inferior completa
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
    "➡️ <code>/precio</code> o botón 🟢🔴 <b>P2P~USDT</b> — Muestra las tasas reales BCV, precios P2P.\n"
    "➡️ <code>/intervencion</code> o botón 📊<b>Intervención</b> — Desglose de bolívares requeridos para la compra de dólares oficiales.\n"
    "➡️ <code>/bpay</code> o botón 🔸<b>BPay</b>🔸— Guía paso a paso para cargar USD bancarios a Binance.\n"
    "➡️ <code>/gpay</code> o botón 🔹<b>GPay</b>🔹— Ruta alternativa para Deposito USD usando Google Pay.\n\n"
    "💡 <b>Nota:</b> <i>Si eres nuevo, lee con atención ~ Boton 👇🏽📜 Regla de Oro 📜. ¡Evita comprar costoso en el P2P!</i>"
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

TEXTO_SOPORTE = (
    "<b>⚙️ Soporte y Colaboraciones</b>\n\n"
    "Cualquier duda sobre el uso de la herramienta implementada, "
    "puedes consultar directamente a Soporte:\n"
    "👤 <a href='tg://user?id=5073264705'>Enderson García</a>\n\n"
    "<i>Para mantener la funcionalidad y eficiencia de la herramienta, "
    "puedes colaborar de forma voluntaria:</i>\n\n"
    "<b>Donaciones:</b>\n"
    "🔸 <b>Binance ID:</b> <code>214109465</code>\n"
    "🇻🇪 <b>Pago Móvil: BDV 0102 BBVA 0108</b> <code>04145057892</code> <code>23007945</code>\n"
    "🔵 <b>PayPal:</b> <code>@ender310</code>\n"
    "🟡 <b>Transferencia Bancaria:</b> <code>01080066810100257971</code>\n"
    "🇻🇪 <code>01020435610001901072</code>\n"
    "<i>(Toca sobre los datos para copiarlos)</i>"
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
    """Retorna la tasa y fecha actuales guardadas en memoria desde el Cazador BCV."""
    tasa = CACHE_TASAS.get("bcv_tasa", 745.64)
    fecha = CACHE_TASAS.get("bcv_fecha", "2026-07-30")
    return tasa, fecha
    
    
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
        "publisherType": "merchant",
        "page": 1,
        "rows": 10,
        "tradeType": tipo_operacion.upper(),
        "transAmount": str(int(monto_bs)),
        "filterType": "tradable",
        "additionalKycVerifyFilter": 0,
        "shieldMerchantAds": False,
        "periods": []
    }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=(2.0, 2.0))
        if r.status_code == 200:
            datos = r.json().get('data', [])
            if datos:
                for elemento in datos:
                    adv = elemento.get('adv', {})
                    advertiser = elemento.get('advertiser', {})

                    precio = adv.get('price')
                    user_status = advertiser.get('userStatus', '')
                    user_type = advertiser.get('userType', '')

                    # 1. Ignorar usuarios bloqueados o inactivos
                    if user_status in ['BLOCKED', 'INACTIVE']:
                        continue

                    # 2. FILTRO DEFINITIVO DE RESTRINGIDOS
                    classifying = adv.get('classifying') or []
                    is_restricted = adv.get('isRestricted') or adv.get('restricted') or False
                    trade_conditions = bool(adv.get('tradeTypeCondition'))
                    adv_conditions = adv.get('advConditions') or adv.get('classificationConditions')
                    has_conditions = bool(adv_conditions) if adv_conditions is not None else False

                    # Si el anuncio requiere condiciones especiales o tiene restricciones en 'classifying'
                    if is_restricted or trade_conditions or has_conditions or len(classifying) > 0:
                        continue

                    # 3. Solo aceptar comerciante verificado
                    if user_type != 'merchant':
                        continue

                    if precio:
                        return float(precio)
    except Exception as e:
        print(f"⚠️ Error conectando con Binance P2P: {e}")

    return None
                    

# --- CACHÉ GLOBAL DE TASAS ---
CACHE_TASAS = {
    "bcv_tasa": 745.64,
    "bcv_tasa_anterior": 744.23,
    "bcv_fecha": "2026-07-30",
    "rangos": {} # Guardará las tasas calculadas por rango
}

# --- PERSISTENCIA EN DISCO ---
ARCHIVO_CACHE = "cache_tasas.json"

def guardar_cache_en_disco():
    try:
        with open(ARCHIVO_CACHE, "w", encoding="utf-8") as f:
            json.dump(CACHE_TASAS, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error guardando caché en disco: {e}")

def cargar_cache_de_disco():
    global CACHE_TASAS
    if os.path.exists(ARCHIVO_CACHE):
        try:
            with open(ARCHIVO_CACHE, "r", encoding="utf-8") as f:
                CACHE_TASAS.update(json.load(f))
                print("💾 ¡Tasas recuperadas con éxito desde el disco!")
        except Exception as e:
            print(f"Error leyendo caché de disco: {e}")
            
def actualizar_cache_segundo_plano():
    global CACHE_TASAS
    while True:
        try:
            # Leemos la tasa BCV actual almacenada en memoria (la que envía el cazador)
            tasa_bcv = CACHE_TASAS.get("bcv_tasa", 745.64)
            tasa_bcv_ajustada = tasa_bcv * 1.005

            ranges_def = [
                ("Rango Pequeño ($50 - $100)", 50.0),
                ("Rango Mediano ($100 - $300)", 150.0),
                ("Rango Mayor ($500+)", 500.0),
            ]

            nuevos_rangos = {}
            for nombre, usd_ref in ranges_def:
                monto_bs = usd_ref * tasa_bcv_ajustada
                compra = obtener_tasa_binance_p2p("BUY", monto_bs) or 0.0
                venta = obtener_tasa_binance_p2p("SELL", monto_bs) or 0.0
                nuevos_rangos[usd_ref] = {
                    "nombre": nombre,
                    "compra": compra,
                    "venta": venta
                }

            CACHE_TASAS["rangos"] = nuevos_rangos
            guardar_cache_en_disco()  # 👈 AGREGA ESTA LÍNEA AQUÍ (alrededor de la línea 311)

        except Exception as e:
            print(f"Error actualizando caché: {e}")

        time.sleep(60)
        
threading.Thread(target=actualizar_cache_segundo_plano, daemon=True).start()

def refrescar_tasas_en_vivo():
    global CACHE_TASAS
    tasa_bcv = CACHE_TASAS.get("bcv_tasa", 745.64)
    fecha_bcv = CACHE_TASAS.get("bcv_fecha", "2026-07-30")

    tasa_bcv_ajustada = tasa_bcv * 1.005
    rangos_def = [
        ("Rango Pequeño ($50 - $100)", 50.0),
        ("Rango Mediano ($100 - $300)", 150.0),
        ("Rango Mayor ($500+)", 500.0)
    ]

    nuevos_rangos = {}
    for nombre, usd_ref in rangos_def:
        monto_bs = usd_ref * tasa_bcv_ajustada
        try:
            compra = obtener_tasa_binance_p2p("BUY", monto_bs) or 0.0
            venta = obtener_tasa_binance_p2p("SELL", monto_bs) or 0.0
        except Exception as e:
            print(f"Error al obtener tasas P2P para {nombre}: {e}")
            compra, venta = 0.0, 0.0
        nuevos_rangos[usd_ref] = {
            "nombre": nombre,
            "compra": compra,
            "venta": venta
        }

    CACHE_TASAS["rangos"] = nuevos_rangos

def construir_monitor_texto_html():
    tasa_bcv = CACHE_TASAS.get("bcv_tasa", 745.64)
    fecha_valor_bcv = CACHE_TASAS.get("bcv_fecha", "30 Julio 2026")
    tasa_intervencion = tasa_bcv * 1.005

    texto = (
        f"🖥️ <b>Monitor de Tasas Arbitraje P2P</b>\n"
        f"<blockquote>📅 <b>Vigencia BCV:</b> {fecha_valor_bcv}</blockquote>\n\n"
        f"<blockquote>🏦 <b>BCV Oficial:</b> <code>{tasa_bcv:.2f}</code> Bs</blockquote>\n"
        f"⚖️ <b>BCV + 0.5%:</b> <code>{tasa_intervencion:.2f}</code> Bs\n"
        f"<i>🛡️ <b>Filtros activos:</b> Verificados | Comerciables 🟡 | Pago: Todos 🔻</i>\n"
        f"----------------------------------------\n\n"
    )

    rangos_cache = CACHE_TASAS.get("rangos", {})
    emojis_rangos = {50.0: "🥉", 150.0: "🥈", 500.0: "🥇"}

    for usd_ref in [50.0, 150.0, 500.0]:
        emoji_rango = emojis_rangos.get(usd_ref, "📌")
        datos = rangos_cache.get(usd_ref) or rangos_cache.get(float(usd_ref)) or rangos_cache.get(str(usd_ref))

        if datos and datos.get("compra", 0) > 0 and datos.get("venta", 0) > 0:
            nombre_rango = datos["nombre"]
            tasa_compra = datos["compra"]
            tasa_venta = datos["venta"]

            # Corrección aquí: se calcula usando tasa_intervencion (BCV + 0.5%)
            filtro_bcv_bs = usd_ref * tasa_intervencion
            spread = tasa_venta - tasa_compra
            porcentaje_spread = (spread / tasa_compra) * 100 if tasa_compra > 0 else 0.0

            texto += f"{emoji_rango} <b>{nombre_rango}</b>\n"
            texto += f"🟢 <b>Compra USDT:</b> <code>{tasa_compra:.2f}</code> Bs\n"
            texto += f"🔴 <b>Venta:</b> <code>{tasa_venta:.2f}</code> Bs\n"

            if usd_ref == 500.0:
                texto += f"    💡 <i>(Filtro base: ~{filtro_bcv_bs:,.0f} Bs)</i>\n"

            texto += f"📈 <b>Spread:</b> <code>{spread:.2f}</code> Bs ({porcentaje_spread:.2f}%)\n"
            texto += f"----------------------------------------\n"
        else:
            nombre_def = "Rango Pequeño" if usd_ref == 50.0 else ("Rango Mediano" if usd_ref == 150.0 else "Rango Grande")
            texto += f"{emoji_rango} <b>{nombre_def}</b>\n⚠️ <i>Cargando tasas en segundo plano...</i>\n"
            texto += f"----------------------------------------\n"

    hora_actual = (datetime.now() - timedelta(hours=4)).strftime("%I:%M:%S %p")
    texto += f"\n🕒 <i>Última actualización: {hora_actual}</i>"

    return texto

def construir_intervencion_texto_html(user=None, porcentaje=None):
    if porcentaje is None:
        if user and es_admin_especial(user):
            porcentaje = 1.0
        else:
            porcentaje = 0.5

    porcentaje_txt = "1%" if porcentaje == 1.0 else "0.5%"

    tasa_bcv = CACHE_TASAS.get("bcv_tasa", 745.64)
    tasa_anterior = CACHE_TASAS.get("bcv_tasa_anterior", 744.23)
    fecha_valor_bcv = CACHE_TASAS.get("bcv_fecha", "30 Julio 2026")

    diferencia = tasa_bcv - tasa_anterior

    if diferencia > 0:
        texto_tendencia = f"✅ BCV AUMENTÓ {abs(diferencia):.2f} BS PARA SU FECHA VALOR BCV 📅"
    elif diferencia < 0:
        texto_tendencia = f"🔻 BCV BAJÓ {abs(diferencia):.2f} BS PARA SU FECHA VALOR BCV 📅"
    else:
        texto_tendencia = f"🔹 BCV MANTIENE SU TASA PARA SU FECHA VALOR BCV 📅"

    tasa_intervencion = tasa_bcv * (1 + (porcentaje / 100))

    texto = (
        f"🚨 <b>¿Cuántos bolívares necesitas para comprar en Intervención?</b>\n\n"
        f"<blockquote>📅 <b>Fecha Valor BCV:</b> {fecha_valor_bcv}</blockquote>\n"
        f"<blockquote>{texto_tendencia}</blockquote>\n"
        f"🏦 <b>Tasa BCV Oficial:</b> <code>{tasa_bcv:.2f}</code> Bs\n"
        f"⚖️ <b>Tasa Intervención:</b> <code>{tasa_intervencion:.2f}</code> Bs ({porcentaje_txt} Agregado)\n"
        f"----------------------------------------\n"
    )

    for monto_usd in range(100, 1100, 100):
        monto_bs = monto_usd * tasa_intervencion
        texto += f"💵 <b>{monto_usd} USD</b> ➡️ Bs: <code>{monto_bs:,.0f}</code>\n"

    return texto
    
# ==========================================
#     MANEJADORES DE COMANDOS Y BOTONES
# ==========================================
            
@bot.message_handler(commands=['start'])
def handle_start(message):
    if message.chat.type == "private":
        # 1. SI ES ADMINISTRADOR VIP
        if es_admin_vip(bot, message.from_user):
            # Teclado ultralimpio para Administradores
            markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add(KeyboardButton("🟢 P2P-USDT 🔴"), KeyboardButton("📊 Intervencion 📊"))
            markup.add(KeyboardButton("⚙️ Soporte"))
            
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
                "📢 <b>Únete a la comunidad oficial aquí:</b> @COMUNIDADAS04\n\n"
                "<i>Una vez te hayas unido, vuelve a presionar /start.</i>"
            )
            bot.send_message(message.chat.id, texto_bloqueo, parse_mode="HTML")
            return

        # Mensaje recargado con teclado completo para novatos
        bot.send_message(message.chat.id, TEXTO_START, parse_mode="HTML", reply_markup=obtener_teclado_privado())
        

# Manejador para /precio y el botón P2P
@bot.message_handler(commands=['precio', 'p2p'])
@bot.message_handler(func=lambda m: m.text and m.text.strip() == "🟢 P2P-USDT 🔴")
def handle_precio_comando(message):
    procesar_precio(message)

# Manejador para el botón de Intervención y el comando /intervencion
@bot.message_handler(commands=['intervencion'])
@bot.message_handler(func=lambda m: m.text and m.text.strip() == "📊 Intervencion 📊")
def handle_intervencion_comando(message):
    procesar_intervencion(message)

# Manejador para los comandos /bpay y /gpay
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
        
@bot.message_handler(func=lambda message: message.text and any(x in message.text for x in ["P2P-USDT", "📊 Intervencion 📊", "Regla de Oro", "GPay", "BPay", "Soporte"]))
def handle_botones_menu(message):
    if message.chat.type == "private":
        if message.text == "🟢 P2P~USDT 🔴":
            procesar_precio(message)
        elif message.text == "📊 Intervencion 📊":
            procesar_intervencion(message)
        elif message.text == "📜 Regla de Oro 📜":
            procesar_regla_oro(message) # <-- NUEVA LLAMADA
        elif message.text in ["🔶 BPay 🔶", "🔵 GPay 🔵"]:
            procesar_guias(message)
        elif message.text == "⚙️ Soporte":
            procesar_soporte(message)
# ==========================================
# REEMPLAZO LIMPIO PARA CHAT PRIVADO
# ==========================================
ultimos_mensajes_privados = {}

def enviar_o_reemplazar_privado(chat_id, user_id, texto, reply_markup=None):
    if user_id in ultimos_mensajes_privados:
        try:
            bot.delete_message(chat_id, ultimos_mensajes_privados[user_id])
        except Exception:
            pass

    try:
        # Intento 1: Enviar con formato HTML
        nuevo_msg = bot.send_message(
            chat_id,
            texto,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    except Exception as e:
        print(f"⚠️ Falló el envío HTML (Error 400), enviando texto plano: {e}")
        # Intento 2 (Fallback): Si el HTML falla, envía el mensaje sin parse_mode para que no rompa
        nuevo_msg = bot.send_message(
            chat_id,
            texto,
            reply_markup=reply_markup
        )

    if nuevo_msg:
        ultimos_mensajes_privados[user_id] = nuevo_msg.message_id
    return nuevo_msg
            
# ==========================================
#  LÓGICA CON AUTODESTRUCCIÓN Y LIMPIEZA
# ==========================================
def procesar_precio(message):
    # --- FILTRO DE SEGURIDAD GENERAL ---
    if not es_chat_permitido(bot, message, CHATS_PERMITIDOS, USUARIOS_AUTORIZADOS, CREADOR_ID):
        return  # Si el canal no está autorizado y el creador NO está adentro, no hace nada.

    user_id = message.from_user.id
    chat_id = message.chat.id
    

    # --- 1. CHAT PRIVADO ---
    if message.chat.type == "private":
        # 👑 ORDEN DE MANDO: Borra el comando enviado por el usuario si empieza con '/'
        if message.text and message.text.strip().startswith('/'):
            try:
                bot.delete_message(chat_id, message.message_id)
            except Exception:
                pass

        if not usuario_esta_unido(user_id):
            bot.reply_to(message, "❌ No tienes acceso. Debes unirte al canal oficial para usar el bot.")
            return
            
        try:
            # 1. Armamos el monitor base
            monitor_base = construir_monitor_texto_html()

            # Mensaje de invitación exclusivo para usuarios comunes
            aviso_regla = (
                "\n\n👉 <b>¿Quieres saber cómo calcular tus ganancias paso a paso?</b>\n"
                "Presiona el botón <b>📜 Regla de Oro 📜</b> en el menú de abajo. 👇🏽👇🏽"
            )

            # 2. EVALUACIÓN DE PRIVILEGIOS
            if es_admin_vip(bot, message.from_user):
                # Admin VIP: Monitor 100% limpio sin texto extra
                texto_completo = monitor_base
            else:
                # Usuario Común: Monitor con la invitación al botón
                texto_completo = monitor_base + aviso_regla

            # 3. Teclado flotante (Inline) de Actualizar Tasas
            markup_tasas = InlineKeyboardMarkup()
            markup_tasas.add(InlineKeyboardButton("🔄 Actualizar Tasas", callback_data="refrescar_tasas"))

            enviar_o_reemplazar_privado(
                chat_id,
                user_id,
                texto_completo,
                reply_markup=markup_tasas
            )
            return

        except Exception as e:
            print(f"Error en precio privado: {e}")
            bot.send_message(chat_id, "❌ Error temporal al obtener tasas. Inténtalo de nuevo en unos segundos.")
            return

    # --- 2. EN GRUPOS ---
    # A) Borramos inmediatamente el mensaje del comando ejecutado (sea Admin o Usuario)
    try:
        bot.delete_message(chat_id, message.message_id)
    except Exception:
        pass
    if str(user_id) == str(CREADOR_ID) or es_admin_vip(bot, message.from_user) or es_administrador(bot, chat_id, user_id, message.from_user):
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
    # --- FILTRO DE SEGURIDAD GENERAL ---
    if not es_chat_permitido(bot, message, CHATS_PERMITIDOS, USUARIOS_AUTORIZADOS, CREADOR_ID):
        return  # Si el canal no está autorizado y el creador NO está adentro, no hace nada.

    user_id = message.from_user.id
    chat_id = message.chat.id


    # --- 1. CHAT PRIVADO ---
    if message.chat.type == "private":
        # 👑 ORDEN DE MANDO: Borra el comando enviado por el usuario si empieza con '/'
        if message.text and message.text.strip().startswith('/'):
            try:
                bot.delete_message(chat_id, message.message_id)
            except Exception:
                pass

        if not usuario_esta_unido(user_id):
            bot.reply_to(message, "❌ No tienes acceso. Debes unirte al canal oficial para usar el bot.")
            return

        # Creamos el botón flotante para actualizar
        markup_intervencion = InlineKeyboardMarkup()
        markup_intervencion.add(InlineKeyboardButton("🔄 Actualizar Cálculo", callback_data="refrescar_intervencion"))

        # 🎯 EVALUACIÓN DE EXCEPCIÓN 1%:
    
        # Evaluamos si es el admin especial pasando el usuario correctamente como primer parámetro
        if es_admin_especial(message.from_user):
            # Para el admin especial calcula al 1.0%
            texto_intervencion = construir_intervencion_texto_html(user=message.from_user, porcentaje=1.0)
        else:
            # Para los usuarios normales calcula al 0.5%
            texto_intervencion = construir_intervencion_texto_html(user=message.from_user, porcentaje=0.5)

        enviar_o_reemplazar_privado(
            chat_id,
            user_id,
            texto_intervencion,
            reply_markup=markup_intervencion
        )
        return

      # --- 2. EN GRUPOS ---
    try:
        bot.delete_message(chat_id, message.message_id)
    except Exception:
        pass

    es_admin_g = False
    try:
        es_admin_g = es_administrador(bot, chat_id, user_id, message.from_user)
    except Exception:
        es_admin_g = False

    if str(user_id) == str(CREADOR_ID) or es_admin_vip(bot, message.from_user) or es_admin_g:
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
                construir_intervencion_texto_html(message.from_user),
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
    # Línea 767 corregida:
    es_bpay = "bpay" in message.text.lower()

    # --- 1. CHAT PRIVADO ---
    if message.chat.type == "private":
        # 👑 ORDEN DE MANDO: Borra el comando enviado por el usuario si empieza con '/'
        if message.text and message.text.strip().startswith('/'):
            try:
                bot.delete_message(chat_id, message.message_id)
            except Exception:
                pass

        if not usuario_esta_unido(user_id):
            bot.reply_to(message, "❌ No tienes acceso. Debes unirte al canal oficial para usar el bot.")
            return   
            
        texto_guia = TEXTO_BPAY if es_bpay else TEXTO_GPAY

        enviar_o_reemplazar_privado(
            chat_id,
            user_id,
            texto_guia
        )
        return  # 👈 Este return corta la función AQUÍ si es privado

    # --- 2. EN GRUPOS (SILENCIO ABSOLUTO Y BORRADO AUTOMÁTICO) ---
    # Se ejecuta solo si el mensaje NO es privado.
    try:
        bot.delete_message(chat_id, message.message_id)
    except Exception:
        pass
        
def procesar_regla_oro(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    # --- 1. CHAT PRIVADO ---
    if message.chat.type == "private":
        # Borra el comando enviado por el usuario si empieza con '/'
        if message.text and message.text.strip().startswith('/'):
            try:
                bot.delete_message(chat_id, message.message_id)
            except Exception:
                pass

        if not usuario_esta_unido(user_id):
            bot.reply_to(message, "❌ No tienes acceso. Debes unirte al canal oficial para usar el bot.")
            return

        enviar_o_reemplazar_privado(
            chat_id,
            user_id,
            TEXTO_REGLA_ORO_HTML
        )
        return

    # --- 2. EN GRUPOS (SILENCIO ABSOLUTO Y BORRADO AUTOMÁTICO) ---
    try:
        bot.delete_message(chat_id, message.message_id)
    except Exception:
        pass
def procesar_soporte(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    # --- 1. CHAT PRIVADO ---
    if message.chat.type == "private":
        if message.text and message.text.strip().startswith('/'):
            try:
                bot.delete_message(chat_id, message.message_id)
            except Exception:
                pass

        if not usuario_esta_unido(user_id):
            bot.reply_to(message, "❌ No tienes acceso. Debes unirte al canal oficial para usar el bot.")
            return

        enviar_o_reemplazar_privado(
            chat_id,
            user_id,
            TEXTO_SOPORTE
        )
        return  # Corta la ejecución si es privado

    # --- 2. EN GRUPOS (SILENCIO ABSOLUTO Y BORRADO AUTOMÁTICO) ---
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

    # 1. Responder de inmediato al botón
    bot.answer_callback_query(call.id, text="🔄 Actualizando tasas en vivo...")

    try:
        # 2. Forzamos la actualización desde Binance
        refrescar_tasas_en_vivo()
        monitor_fresco = construir_monitor_texto_html()


        aviso_regla = (
            "\n\n💡 <b>¿Quieres saber cómo calcular tus ganancias paso a paso?</b>\n"
            "Presiona el botón <b>📜 Regla de Oro 📜</b> en el menú de abajo. 👇👇"
        )

        if es_admin_vip(bot, call.from_user):
            texto_editado = monitor_fresco 
        else:
            texto_editado = monitor_fresco + aviso_regla 

        # 3. Construimos el teclado
        markup_tasas = InlineKeyboardMarkup()
        if call.message.chat.id == CANAL_ADMINS or es_admin_vip(bot, call.from_user):
            markup_tasas.row(
                InlineKeyboardButton("🔄 Actualizar Tasas", callback_data="refrescar_tasas"),
                InlineKeyboardButton("🗑️ Borrar", callback_data="borrar_mensaje")
            )
        else:
            markup_tasas.add(InlineKeyboardButton("🔄 Actualizar Tasas", callback_data="refrescar_tasas"))

        # 4. Editamos el mensaje
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=texto_editado,
            parse_mode="HTML",
            reply_markup=markup_tasas
        )

    except Exception as e:
        print(f"Aviso al refrescar tasas: {e}")

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
        if call.message.chat.id == CANAL_ADMINS or es_admin_vip(bot, call.from_user):
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
    # 1. Verificamos si es chat privado O si tiene rango en un grupo/canal
    es_privado = call.message.chat.type == "private"
    
    if es_privado:
        es_admin_o_vip = es_admin_vip(bot, call.from_user)
    else:
        es_admin_o_vip = es_admin_vip(bot, call.from_user) or es_administrador(bot, call.message.chat.id, call.from_user.id, call.from_user)

    if not es_admin_o_vip:
        bot.answer_callback_query(
            call.id,
            text="❌ Solo los administradores pueden eliminar esta tabla.",
            show_alert=True
        )
        return

    # 2. Borra la tabla al instante (sea de precio o intervención)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id, text="🗑️ Mensaje borrado.")
    except Exception:
        bot.answer_callback_query(
            call.id,
            text="⚠️ No se pudo eliminar el mensaje o ya fue borrado."
        )
        
# ==========================================
# FILTRO DE SEGURIDAD GENERAL (ABAJO)
# ==========================================

@bot.message_handler(func=lambda m: m.chat.type != 'private', content_types=['text'])
def filtro_seguridad_chat(message):
    # 1. Si el mensaje empieza con '/', LO BORRAMOS DE INMEDIATO (Sea cual sea el comando)
    if message.text and message.text.strip().startswith("/"):
        # Intentamos usar la limpieza de Group Help para respetar el cooldown si aplica
        if not limpiar_comandos_chat(bot, message):
            # Si no era de Group Help, lo borramos de todos modos para evitar spam
            try:
                bot.delete_message(message.chat.id, message.message_id)
            except Exception:
                pass
        return  # Detenemos aquí para que no siga procesando nada más

    # 2. Verificamos si es administrador
    es_admin = es_administrador(bot, message.chat.id, message.from_user.id, message.from_user)

    # 3. Si un usuario común pegó un reporte oficial, lo borra y se detiene
    if validar_copia_pega(bot, message, es_admin):
        return
            
# ==========================================
# RECEPTOR WEBHOOK PARA EL CAZADOR
# ==========================================

CLAVE_SECRETA_BCV = os.getenv("CLAVE_SECRETA_BCV")

class WebhookHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/actualizar_bcv":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)

            try:
                datos = json.loads(post_data.decode('utf-8'))
                clave = datos.get("clave")
                tasa = datos.get("tasa")
                fecha = datos.get("fecha")

                if clave != CLAVE_SECRETA_BCV:
                    self.send_response(403)
                    self.end_headers()
                    self.wfile.write(b'{"status":"error","message":"No autorizado"}')
                    return

                if tasa and fecha:
                    tasa_nueva = float(tasa)
                    tasa_actual = CACHE_TASAS.get("bcv_tasa", tasa_nueva)

                    # Si la tasa recibida es distinta a la actual, la actual pasa a ser la anterior
                    if tasa_nueva != tasa_actual:
                        CACHE_TASAS["bcv_tasa_anterior"] = tasa_actual

                    CACHE_TASAS["bcv_tasa"] = tasa_nueva
                    CACHE_TASAS["bcv_fecha"] = str(fecha)

                    # Agrega esto para recalcular rangos P2P inmediatamente al recibir
                    tasa_ajustada = tasa_nueva * 1.005
                    ranges_def = [
                        ("Rango Pequeño ($50 - $100)", 50.0),
                        ("Rango Mediano ($100 - $300)", 150.0),
                        ("Rango Mayor ($500+)", 500.0),
                    ]
                    nuevos_rangos = {}
                    for nombre, usd_ref in ranges_def:
                        monto_bs = usd_ref * tasa_ajustada
                        compra = obtener_tasa_binance_p2p("BUY", monto_bs) or 0.0
                        venta = obtener_tasa_binance_p2p("SELL", monto_bs) or 0.0
                        nuevos_rangos[usd_ref] = {"nombre": nombre, "compra": compra, "venta": venta}
                    
                    CACHE_TASAS["rangos"] = nuevos_rangos

                    # 💾 Guarda la copia física en el disco
                    guardar_cache_en_disco()

                    print(f"🔥 [WEBHOOK] Tasa BCV actualizada por El Cazador: {tasa_nueva} | Fecha: {fecha}")

                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(b'{"status":"success","message":"Tasa actualizada en memoria y disco"}')
                    return

            except Exception as e:
                print(f"Error procesando webhook: {e}")

            self.send_response(400)
            self.end_headers()

def iniciar_servidor_receptor():
    port = int(os.getenv("PORT", 8080))
    handler = WebhookHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"🚀 Receptor de tasas escuchando en el puerto {port}")
        httpd.serve_forever()
                
# ==========================================
#            EJECUCIÓN DEL BOT
# ==========================================

if __name__ == "__main__":
    # 💾 Carga la tasa guardada en disco antes de iniciar
    cargar_cache_de_disco()

    # Limpia webhooks y descarta actualizaciones pendientes
    try:
        bot.remove_webhook(drop_pending_updates=True)
        time.sleep(1)
    except Exception:
        pass

    iniciar_modulo_anuncios(bot)
    print("🚀 Bot Maestro en línea con limpieza automática y temporizador de 5 min...")

    # Inicia el receptor webhook en segundo plano
    threading.Thread(target=iniciar_servidor_receptor, daemon=True).start()

    # Arranca el polling limpio
    bot.infinity_polling()
    
    
    
