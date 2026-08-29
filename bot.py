import http.server
import socketserver
import os
import json
import requests
import telebot
import time
import threading
import locale
from datetime import datetime, timedelta
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telebot import types
from captcha import setup_verification_handlers
from seguridad import validar_copia_pega, es_admin_vip, es_admin_especial, es_administrador, es_chat_permitido
from seguridad import limpiar_comandos_chat, registrar_filtro_anti_raid, registrar_limpiador_servicio
from calculadora import registrar_calculadora
from ia_consulta import registrar_ia_consulta
from anuncios import iniciar_modulo_anuncios, setup_comando_aviso
from emojis import TG_EMOJIS, e
import re
import urllib3
from bs4 import BeautifulSoup
# Desactivar avisos de certificados SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import redis
# Conexión a Redis
redis_url = os.getenv("REDIS_URL")
r = redis.from_url(redis_url) if redis_url else None


# ==========================================
# CONFIGURACIÓN Y VARIABLES GLOBALES
# ==========================================
TOKEN_TELEGRAM = os.getenv("TOKEN_TELEGRAM")
bot = telebot.TeleBot(TOKEN_TELEGRAM)

registrar_filtro_anti_raid(bot)

registrar_limpiador_servicio(bot)

BOT_USERNAME = "BancoIDV_bot" # Reemplaza con el alias de tu bot sin el @

# ==========================================
# CONFIGURACIÓN Y VARIABLES GLOBALES (PRODUCCIÓN)
# ==========================================

# Otros Canales/Grupos Administrativos
CANAL_SECUNDARIO = -1004378497075

# Canales de Pruebas (puedes mantenerlos o cambiarlos)
CANAL_PRUEBA = -1004473532809
CANAL_PRINCIPAL_IDV = -1003950050807

# USUARIOS AUTORIZADOS Y CREADOR (¡Restaurar estas líneas!)
USUARIOS_AUTORIZADOS = [5073264705, 791436853]
CREADOR_ID = 5073264705

# 🟢 REGISTRAR COMANDOS PRIORITARIOS AQUÍ (Arriba de los demás handlers)
setup_comando_aviso(bot, es_admin_vip, USUARIOS_AUTORIZADOS)

# Lista unificada de chats donde el bot responderá a comandos de canal (/p, /i, /tasas)
CHATS_PERMITIDOS = [ 
    CANAL_PRUEBA
]

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
def obtener_teclado_privado(user=None):
    if user and es_admin_vip(bot, user):
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(KeyboardButton("🟢 P2P-USDT 🔴"), KeyboardButton("📊 Intervencion 📊"))
        markup.add(KeyboardButton("📟 Calculadora"), KeyboardButton("⚙️ Soporte"))
        markup.add(KeyboardButton("🤖 IA Consulta"), KeyboardButton("📊 Arbitraje & Reposición"))
        return markup

    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_precio = KeyboardButton("🟢 P2P-USDT 🔴")
    btn_intervencion = KeyboardButton("📊 Intervencion 📊")
    btn_regla = KeyboardButton("📜 Regla de Oro 📜")
    btn_bpay = KeyboardButton("🔶 BPay 🔶")
    btn_gpay = KeyboardButton("🔷 GPay 🔷")
    btn_calculadora = KeyboardButton("📟 Calculadora")
    btn_soporte = KeyboardButton("⚙️ Soporte")
    btn_ia = KeyboardButton("🤖 IA Consulta")
    btn_arbitraje = KeyboardButton("📊 Arbitraje & Reposición")

    markup.add(btn_precio, btn_intervencion)
    markup.add(btn_regla, btn_calculadora)
    markup.add(btn_bpay, btn_gpay)
    markup.add(btn_soporte)
    markup.add(btn_ia)
    markup.add(btn_arbitraje)
    return markup

solicitar_ia_consulta = registrar_ia_consulta(bot, r, obtener_teclado_privado)

def obtener_boton_actualizar_inline():
    markup = InlineKeyboardMarkup()
    btn_refresh = InlineKeyboardButton("🔄 Actualizar Tasas", callback_data="refrescar_tasas")
    markup.add(btn_refresh)
    return markup

# ==========================================
#  TEXTOS ORIGINALES COMPLETOS
# ==========================================
TEXTO_START = (
    "👋 <b>¡Bienvenido al Monitor Oficial ~ Arbitraje P2P!</b>\n\n"
    "Este bot es tu herramienta aliada para proteger tu capital y generar ganancias reales en Venezuela 🇻🇪. Aquí no tienes que adivinar; el sistema calcula todo por ti.\n\n"
    "🚀 <b>¿Cómo empezar? Usa el menú interactivo de botones aquí abajo o escribe los comandos:</b>\n"
    "➡️ <code>/p</code> o botón 🟢🔴 <b>P2P~USDT</b> — Muestra las tasas reales BCV, precios P2P.\n"
    "➡️ <code>/i</code> o botón 📊<b>Intervención</b> — Desglose de bolívares requeridos para la compra de dólares oficiales.\n"
    "➡️ <code>/bp</code> o botón 🔸<b>BPay</b>🔸— Guía paso a paso para cargar USD bancarios a Binance.\n"
    "➡️ <code>/gp</code> o botón 🔹<b>GPay</b>🔹— Ruta alternativa para Deposito USD usando Google Pay.\n\n"
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
    f"2️⃣ Pásalos a Binance mediante /bp o /gp (Depósito USD).\n"
    f"3️⃣ Convierte a USDT y vende usando la tasa de <code>🔴 Venta</code> de este monitor.\n\n"
    f"🛡️ <b>Estrategia de Capital Seguro:</b>\n"
    f"Al vender en VES, consulta mañana este bot. Usa solo los bolívares necesarios para volver a comprar tu capital base en el banco (<code>BCV + 0.5%</code>). <b>¡Deja tus ganancias acumuladas en USDT dentro de Binance como tu colchón de ahorro seguro!</b>"
)

TEXTO_SOPORTE = (
    f"{e('PROGRAMADOR', '🐱')} <b>⚙️ Soporte y Colaboraciones</b>\n\n"
    f"Cualquier duda sobre el uso de la herramienta implementada, "
    f"puedes consultar directamente a Soporte: {e('github', '🐱')}\n"
    f" <a href=\"tg://user?id=5073264705\">Enderson García</a>\n\n"
    f"<i>Para mantener la funcionalidad y eficiencia de la herramienta, "
    f"puedes colaborar de forma voluntaria:</i>\n\n"
    f"<b>Donaciones:</b>\n"
    f"{e('BINANCE_ESPEJO', '💵')} <b>Binance ID:</b> <code>214109465</code>\n"
    f"{e('pago_movil', '💳')} {e('bdv1', '🔉')} <b>Pago Móvil BDV 0102:</b> <code>04145057892</code> <code>23007945</code>\n"
    f"{e('pro', '🕘')} <b>BBVA 0108:</b> <code>04145057892</code>\n"
    f"{e('paypal', '🌐')} <b>PayPal:</b> <code>@ender310</code>\n"
    f"{e('BCV', '🤝')} <b>Transferencia Bancaria:</b>\n"
    f"{e('bdv1', '🔉')} <code>01020435610001901072</code>\n"
    f"{e('pro', '🕘')} <code>01080066810100257971</code>\n"
    f"{e('clic', '🎯')} <i>(Toca sobre los datos para copiarlos)</i>\n"
    f"-----------------------------------------\n"
)

# ==========================================
#  LÓGICA DE PROCESAMIENTO Y APIS
# ==========================================
def usuario_esta_unido(user, user_id=None):
    """
    Verifica si un usuario tiene acceso permitido al bot.
    Funciona si recibe un objeto 'user' de Telegram O un 'user_id' (entero/string).
    """
    # Determinar el ID real sin importar cómo lo envíe captcha.py
    if hasattr(user, 'id'):
        actual_id = user.id
    elif user_id is not None:
        actual_id = user_id
    else:
        actual_id = user

    if not actual_id:
        return False

    # 1. El Creador Supremo siempre tiene acceso
    if str(actual_id) == str(CREADOR_ID):
        return True

    # 2. Si es Admin VIP (creamos un objeto simple si solo tenemos la ID)
    try:
        user_obj = user if hasattr(user, 'id') else type('UserObj', (object,), {'id': actual_id, 'username': ''})()
        if es_admin_vip(bot, user_obj):
            return True
    except Exception:
        pass

    # 3. Verificamos si pertenece a cualquiera de los chats/canales permitidos
    for chat_id in CHATS_PERMITIDOS:
        try:
            miembro = bot.get_chat_member(chat_id, actual_id)
            if miembro.status in ['creator', 'administrator', 'member']:
                return True
        except Exception:
            continue

    return False

# ===============================================
# DESPACHADOR DE MENÚ Y CAPTCHA
# ===============================================

def enviar_menu_principal(bot, user, chat_id):
    if es_admin_vip(bot, user):
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(KeyboardButton("🟢 P2P-USDT 🔴"), KeyboardButton("📊 Intervencion 📊"))
        markup.add(KeyboardButton("📟 Calculadora"), KeyboardButton("⚙️ Soporte"))
        markup.add(KeyboardButton("🤖 IA Consulta"), KeyboardButton("📊 Arbitraje & Reposición"))
        
        texto_vip = (
            f"<b>👑 ¡Hola, {user.first_name}!</b>\n\n"
            f"Gracias por tu valiosa labor diaria manteniendo el orden en la comunidad ~ Enderson 👏🏽.\n"
            f"<i>⚡ Tienes activo el entorno VIP de trabajo rápido (sin distracciones ni guías de inicio).</i>"
        )
        bot.send_message(chat_id, texto_vip, parse_mode="HTML", reply_markup=markup)
    else:
        markup = obtener_teclado_privado(user)
        bot.send_message(chat_id, TEXTO_START, parse_mode="HTML", reply_markup=markup)


# Inicialización del captcha
setup_verification_handlers(
    bot=bot,
    target_channel_id=CANAL_PRUEBA,
    funcion_menu=enviar_menu_principal,
    funcion_esta_unido=usuario_esta_unido
)

# --- CONEXIÓN A REDIS Y LECTURA DE FUENTE ÚNICA ---
def obtener_datos_bcv_validos():
    """
    Lee directamente de Redis las claves atómicas.
    Si Redis no tiene datos o reinició, usa valores de resguardo.
    """
    try:
        t_hoy = r.get("bcv_tasa_hoy") if r else None
        t_manana = r.get("bcv_tasa_manana") if r else None
        t_anterior = r.get("bcv_tasa_anterior") if r else None
        
        f_hoy = r.get("bcv_fecha_hoy") if r else None
        f_manana = r.get("bcv_fecha_manana") if r else None

        # Decodificar bytes de Redis a string de manera segura
        f_hoy_str = f_hoy.decode('utf-8') if isinstance(f_hoy, bytes) else (f_hoy or "Hoy")
        f_manana_str = f_manana.decode('utf-8') if isinstance(f_manana, bytes) else (f_manana or "Mañana")

        # Conversión segura a float (Valores base de prueba en entorno secundario)
        tasa_hoy = float(t_hoy) if t_hoy and float(t_hoy) > 0 else 791.325
        tasa_manana = float(t_manana) if t_manana and float(t_manana) > 0 else 791.667
        tasa_anterior = float(t_anterior) if t_anterior and float(t_anterior) > 0 else 791.325

        return {
            "tasa_hoy": tasa_hoy,
            "tasa_manana": tasa_manana,
            "tasa_anterior": tasa_anterior,
            "fecha_hoy": f_hoy_str,
            "fecha_manana": f_manana_str
        }
    except Exception as e:
        print(f"⚠️ Error leyendo Redis: {e}")
        return {
            "tasa_hoy": 791.325,
            "tasa_manana": 791.667,
            "tasa_anterior": 791.325,
            "fecha_hoy": "Hoy",
            "fecha_manana": "Mañana"
        }
    

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
        "publisherType": "merchant",  # 👈 Esencial para filtrar comerciantes
        "page": 1,
        "rows": 10,
        "tradeType": tipo_operacion.upper(),
        "transAmount": str(int(monto_bs)),
        "filterType": "tradable",
        "additionalKycVerifyFilter": 0,
        "periods": []
    }

    try:
        # Aumentamos el timeout a 5.0s para evitar fallas silenciosas en Railway
        r = requests.post(url, json=payload, headers=headers, timeout=(5.0, 5.0))
        if r.status_code == 200:
            datos = r.json().get('data', [])
            if datos:
                precios_validos = []
                for elemento in datos:
                    adv = elemento.get('adv', {})
                    advertiser = elemento.get('advertiser', {})

                    precio = adv.get('price')
                    user_status = advertiser.get('userStatus', '')

                    # 1. Ignorar usuarios bloqueados o inactivos
                    if user_status in ["BLOCKED", "INACTIVE"]:
                        continue

                    # 2. FILTRO DEFINITIVO DE RESTRINGIDOS / CONDICIONES ATÍPICAS
                    is_restricted = adv.get('isRestricted') or adv.get('restricted') or False
                    trade_conditions = bool(adv.get('tradeConditions'))  # 👈 Corregido a plural 'tradeConditions'
                    class_conditions = bool(adv.get('classificationConditions'))
                    adv_conditions = bool(adv.get('advConditions'))

                    # Si tiene cualquier tipo de restricción o condición especial, lo saltamos
                    if is_restricted or trade_conditions or class_conditions or adv_conditions:
                        continue

                    if precio:
                        precios_validos.append(float(precio))

                # 3. FILTRO ANTI-FANTASMA (Compara el 1er y 2do precio de la lista)
                if precios_validos:
                    if len(precios_validos) >= 2:
                        # Si la diferencia porcentual con el 2do anuncio es mayor al 2% (anuncio fantasma/desviado)
                        diferencia_porcentual = abs(precios_validos[0] - precios_validos[1]) / precios_validos[1]
                        if diferencia_porcentual > 0.02: 
                            return precios_validos[1]
                    
                    return precios_validos[0]

    except Exception as e:
        print(f"⚠️ Error conectando con Binance P2P: {e}")

    return None

def obtener_tasa_binance_zinli(tipo_operacion, monto_usd=0):
    """
    Obtiene la tasa P2P de Binance para Zinli (USD).
    tipo_operacion: 'BUY' o 'SELL'
    monto_usd: 50, 150, 500, etc.
    """
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    headers = {
        "Accept": "*/*",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    payload = {
        "asset": "USDT",
        "fiat": "USD",
        "merchantCheck": True,
        "publisherType": "merchant",
        "payTypes": ["Zinli"],
        "page": 1,
        "rows": 10,
        "tradeType": tipo_operacion.upper(),
        "transAmount": str(int(monto_usd)) if monto_usd > 0 else "",
        "filterType": "tradable",
        "additionalKycVerifyFilter": 0,
        "periods": []
    }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=(5.0, 5.0))
        if r.status_code == 200:
            datos = r.json().get('data', [])
            precios_validos = []
            for elemento in datos:
                adv = elemento.get('adv', {})
                advertiser = elemento.get('advertiser', {})
                 
                # 1. Descartar cuentas inactivas o bloqueadas
                if advertiser.get('userStatus') in ["BLOCKED", "INACTIVE"]:
                    continue

                # 2. Descartar anuncios con restricciones de cuenta/clase
                is_restricted = adv.get('isRestricted', False)
                trade_conds = adv.get('tradeConditions') or []
                class_conds = adv.get('classConditions') or []

                if is_restricted or len(trade_conds) > 0 or len(class_conds) > 0:
                    continue

                # 3. Extraer precio válido
                precio = adv.get('price')
                if precio and float(precio) > 0:
                    precios_validos.append(float(precio))
            
            if precios_validos:
                return precios_validos[0]
    except Exception as e:
        print(f"⚠️ Error al obtener P2P Zinli: {e}")
    
    return 0.0
    


def obtener_tasa_binance_spot_usdt():
    """Obtiene la tasa real del par USD/USDT ajustada al spread de Binance Convert."""
    # Factor de ajuste para emular el spread de Convert (~1.00015 en lugar del Spot directo)
    FACTOR_SPREAD_CONVERT = 1.00018

    try:
        url_binance = "https://api.binance.com/api/v3/ticker/price?symbol=USDTUSD"
        r = requests.get(url_binance, timeout=3.0)
        if r.status_code == 200:
            precio_raw = float(r.json().get("price", 0.9999))
            tasa_spot = (1 / precio_raw) if precio_raw < 1 else precio_raw
            return round(tasa_spot * FACTOR_SPREAD_CONVERT, 5)
    except Exception:
        pass

    try:
        url_cb = "https://api.coinbase.com/v2/prices/USDT-USD/spot"
        r = requests.get(url_cb, timeout=3.0)
        if r.status_code == 200:
            precio = float(r.json()["data"]["amount"])
            if precio > 0:
                return round(precio * FACTOR_SPREAD_CONVERT, 5)
    except Exception:
        pass

    return 1.00015  # Tasa base de respaldo exacta para Convert

# Registramos la calculadora usando la fuente única de verdad en Redis
solicitar_calculadora = registrar_calculadora(bot, obtener_datos_bcv_validos, obtener_teclado_privado)
                
def actualizar_cache_segundo_plano():
    while True:
        try:
            # 1. Actualizar tasa Spot en Redis
            spot_rate = obtener_tasa_binance_spot_usdt()
            if spot_rate and r:
                r.set("usdt_usd_spot", str(spot_rate))

            # 2. Calcular y actualizar P2P basándose en Redis
            datos_bcv = obtener_datos_bcv_validos()
            tasa_bcv_ajustada = datos_bcv["tasa_hoy"] * 1.005

            ranges_def = [
                ("Rango Menor ($50 - $100)", 50.0),
                ("Rango Medio ($100 - $300)", 150.0),
                ("Rango Mayor ($500+)", 500.0)
            ]

            nuevos_rangos = {}
            for nombre, usd_ref in ranges_def:
                monto_bs = usd_ref * tasa_bcv_ajustada
                compra = obtener_tasa_binance_p2p("BUY", monto_bs) or 0.0
                venta = obtener_tasa_binance_p2p("SELL", monto_bs) or 0.0
                nuevos_rangos[str(usd_ref)] = {
                    "nombre": nombre,
                    "compra": compra,
                    "venta": venta
                }

            if r:
                r.set("p2p_rangos", json.dumps(nuevos_rangos))

        except Exception as e:
            print(f"Error actualizando P2P en segundo plano: {e}")
        
        time.sleep(60)

threading.Thread(target=actualizar_cache_segundo_plano, daemon=True).start()
            

def refrescar_tasas_en_vivo():
    datos_bcv = obtener_datos_bcv_validos()
    tasa_bcv_ajustada = datos_bcv["tasa_hoy"] * 1.005

    ranges_def = [
        ("Rango Menor ($50 - $100)", 50.0),
        ("Rango Medio ($100 - $300)", 150.0),
        ("Rango Mayor ($500+)", 500.0)
    ]

    nuevos_rangos = {}
    for nombre, usd_ref in ranges_def:
        monto_bs = usd_ref * tasa_bcv_ajustada
        try:
            compra = obtener_tasa_binance_p2p("BUY", monto_bs) or 0.0
            venta = obtener_tasa_binance_p2p("SELL", monto_bs) or 0.0
        except Exception as e:
            print(f"Error al obtener tasas P2P para {nombre}: {e}")
            compra, venta = 0.0, 0.0

        nuevos_rangos[str(usd_ref)] = {
            "nombre": nombre,
            "compra": compra,
            "venta": venta
        }

    if r:
        r.set("p2p_rangos", json.dumps(nuevos_rangos))
        

def construir_monitor_canal_html():
    """Genera la ficha resumen simplificada para el Canal Principal con Custom Emojis dinámicos"""
    # Consulta la mejor tasa de compra y venta general
    compra_base = obtener_tasa_binance_p2p("buy", 0) or 0.0
    venta_base = obtener_tasa_binance_p2p("sell", 0) or 0.0

    if compra_base == 0.0 or venta_base == 0.0:
        return f"⚠️ <b>Error temporal al obtener tasas de Binance P2P.</b>"

    spread = round(venta_base - compra_base, 2)
    porcentaje = round((spread / compra_base) * 100, 2) if compra_base > 0 else 0.0
    
    hora_actual = (datetime.now() - timedelta(hours=4)).strftime("%I:%M:%S %p")

    # Emoji dinámico de Spread (SUBIDA si es >= 0, BAJADA si es negativo)
    emoji_spread = e("SUBIDA", "📈") if spread >= 0 else e("BAJADA", "📉")

    # Formato corto usando el diccionario TG_EMOJIS mediante la función e()
    texto = (
        f"{e('BINANCE_P2P', '🪙')} <b>TASAS P2P EN VIVO</b>\n\n"
        f"{e('VERDE', '🟢')} <b>COMPRA USDT:</b> {compra_base:.2f} Bs\n"
        f"{e('ROJO', '🔴')} <b>VENTA USDT:</b> {venta_base:.2f} Bs\n\n"
        f"{emoji_spread} <b>Spread:</b> {spread:.2f} Bs ({porcentaje:.2f}%)\n\n"
        f"{e('MUNDO', '🌎')} <i>Última actualización: {hora_actual}</i>"
    )
    return texto
    

def construir_monitor_texto_html():
    # Extraer datos centralizados de Redis
    datos_bcv = obtener_datos_bcv_validos()

    tasa_hoy = datos_bcv.get("tasa_hoy", 0.0)
    tasa_manana = datos_bcv.get("tasa_manana", 0.0)

    # Lógica de decisión igual a Intervención:
    if tasa_manana > 0 and tasa_manana != tasa_hoy:
        tasa_bcv = tasa_manana
        fecha_valor_bcv = datos_bcv.get("fecha_manana", "Mañana")
    else:
        tasa_bcv = tasa_hoy
        fecha_valor_bcv = datos_bcv.get("fecha_hoy", "Hoy")

    tasa_intervencion = tasa_bcv * 1.005
    
    texto = (
        f"{e('MONITOR', '💻')} <b>Monitor de Tasas Arbitraje P2P</b>\n\n"
        f"<blockquote>{e('CALENDARIO', '🗓')} <b>Vigencia BCV :</b> {fecha_valor_bcv}</blockquote>\n"
        f"<blockquote>{e('BCV', '🏦')} <b>BCV Oficial :</b> <code>{tasa_bcv:.3f}</code> Bs</blockquote>\n"
        f"<blockquote>{e('BALANZA', '⚖️')} <b>BCV + 0.5% :</b> <code>{tasa_intervencion:.3f}</code> Bs</blockquote>\n\n"
        f"{e('ETIQUETA', '🔖')} <b>Filtros Activos:</b> Verificados | Comerciables {e('BOMBILLA', '💡')} | Pago : Todos {e('CHINCHE', '📌')}\n"
        f"-----------------------------------------\n\n"
    )

    # LÍNEA 594 CORREGIDA:
    rangos_cache = {}
    if r:
        try:
            raw_p2p = r.get("p2p_rangos")
            if raw_p2p:
                rangos_cache = json.loads(raw_p2p.decode('utf-8') if isinstance(raw_p2p, bytes) else raw_p2p)
        except Exception as err:
            print(f"Error leyendo p2p_rangos de Redis: {err}") 
    
    # Asignación de rangos según la imagen:
    # 50.0 = Rango Menor (🥉), 150.0 = Rango Mediano (🥈), 500.0 = Rango Mayor (🥇)
    emojis_rangos = {
        50.0: (e("RANGO_3", "🥉"), "Rango Menor (50 - 100)"),
        150.0: (e("RANGO_2", "🥈"), "Rango Medio (100 - 300)"),
        500.0: (e("RANGO_1", "🥇"), "Rango Mayor (500+)")
    }


    for usd_ref in [50.0, 150.0, 500.0]:
        emoji_rango, nombre_def = emojis_rangos.get(usd_ref, (e("RANGO_3", "🥉"), "Rango"))
    
        # 🔍 Probamos todas las variaciones posibles de llaves (str, int, float, str con int)
        datos = (
            rangos_cache.get(str(usd_ref)) or 
            rangos_cache.get(usd_ref) or 
            rangos_cache.get(str(int(usd_ref))) or 
            rangos_cache.get(int(usd_ref))
        )
    
        if datos and datos.get("compra", 0) > 0 and datos.get("venta", 0) > 0:
            nombre_rango = datos.get("nombre", nombre_def)
            tasa_compra = datos["compra"]
            tasa_venta = datos["venta"]

            filtro_bcv_bs = usd_ref * tasa_intervencion
            spread = tasa_venta - tasa_compra
            porcentaje_spread = (spread / tasa_compra) * 100 if tasa_compra > 0 else 0.0

            # Emoji dinámico de Spread (Subida/Bajada)
            emoji_spread = e("SUBIDA", "📈") if spread >= 0 else e("BAJADA", "📉")

            texto += f"{emoji_rango}<b>{nombre_rango}</b>\n"
            texto += f"{e('USDT', '🪙')}{e('VERDE', '🟢')}<b>Compra USDT:</b> <code>{tasa_compra:.2f}</code>Bs\n"
            texto += f"{e('USDT', '🪙')}{e('ROJO', '🔴')}<b>Venta:</b> <code>{tasa_venta:.2f}</code> Bs\n\n"

            if usd_ref == 500.0:
                texto += f"  {e('BOMBILLA', '💡')} <i>Filtro base: ({filtro_bcv_bs:,.0f} Bs)</i>\n"

            texto += f" {emoji_spread} <b>Spread:</b> <code>{spread:.2f}</code> Bs (<code>{porcentaje_spread:.2f}%</code>)\n"
            texto += f"-----------------------------------------\n\n"
        else:
            texto += f"{emoji_rango}<b>{nombre_def}</b>\n"
            texto += f"<i>{e('BOMBILLA', '💡')} Cargando tasas en segundo plano...</i>\n"
            texto += f"-----------------------------------------\n\n"

    hora_actual = (datetime.now() - timedelta(hours=4)).strftime("%I:%M:%S %p")
    texto += f"{e('MUNDO', '🌎')} <i>Última actualización: {hora_actual}</i>"

    return texto


def construir_monitor_zinli_html():
    """Genera la ficha desglosada por rangos para Zinli USD / USDT"""
    
    # Configuración de rangos (Monto, Etiqueta, Emoji)
    emojis_rangos = [
        (50.0, e("RANGO_3", "🥉"), "Rango Menor (50 - 100)"),
        (150.0, e("RANGO_2", "🥈"), "Rango Medio (100 - 300)"),
        (500.0, e("RANGO_1", "🥇"), "Rango Mayor (500+)")
    ]
    
    hora_actual = (datetime.now() - timedelta(hours=4)).strftime("%I:%M:%S %p")
    
    texto = (
        f"<blockquote>{e('MONITOR', '💻')} Monitor {e('zinli', '🔹')} Zinli / {e('USDT', '🪙')}</blockquote>\n\n"
        f"{e('ETIQUETA', '🔖')} <b>Filtros Activos:</b> Verificados | Comercializables {e('BOMBILLA', '💡')} | Pago :{e('zinli', '🔹')} {e('CHINCHE', '📌')}\n"
        f"-----------------------------------------\n\n"
    )

    for monto_ref, emoji_rango, nombre_rango in emojis_rangos:
        compra = obtener_tasa_binance_zinli("buy", monto_ref)
        venta = obtener_tasa_binance_zinli("sell", monto_ref)
        
        spread = round(venta - compra, 3)
        porcentaje_spread = round((spread / compra) * 100, 2) if compra > 0 else 0.0
        
        emoji_spread = e("SUBIDA", "📈") if spread >= 0 else e("BAJADA", "📉")
        
        texto += (
            f"{emoji_rango} <b>{nombre_rango}</b>\n"
            f"{e('USDT', '🪙')} {e('VERDE', '🟢')} <b>Compra:</b> <code>${compra:.3f}</code>\n"
            f"{e('USDT', '🪙')} {e('ROJO', '🔴')} <b>Venta:</b> <code>${venta:.3f}</code>\n\n"
            f"{emoji_spread} <b>Spread:</b> <code>${spread:+.3f}</code> (<code>{porcentaje_spread:+.2f}%</code>)\n"
            f"-----------------------------------------\n"
        )

    texto += f"\n{e('MUNDO', '🌐')} <i>Última actualización: {hora_actual}</i>"
    return texto
    

def construir_intervencion_texto_html(user=None, porcentaje=None):
    if porcentaje is None:
        porcentaje = 1.0 if user and es_admin_especial(user) else 0.5

    porcentaje_txt = "1%" if porcentaje == 1.0 else "0.5%"
    
    # Extraer datos centralizados de Redis
    datos_bcv = obtener_datos_bcv_validos()
    
    tasa_hoy = datos_bcv["tasa_hoy"]
    tasa_manana = datos_bcv["tasa_manana"]
    tasa_anterior = datos_bcv["tasa_anterior"]

    # Lógica de decisión de tasa activa y fecha
    if tasa_manana > 0 and tasa_manana != tasa_hoy:
        tasa_bcv = tasa_manana
        fecha_valor_bcv = datos_bcv["fecha_manana"]
        tasa_base_comparar = tasa_hoy
    else:
        tasa_bcv = tasa_hoy
        fecha_valor_bcv = datos_bcv["fecha_hoy"]
        tasa_base_comparar = tasa_anterior if tasa_anterior > 0 else tasa_hoy

    if tasa_bcv == 0.0:
        return "⚠️ <b>Error:</b> Las tasas del BCV se están cargando desde la base de datos."

    diferencia = round(tasa_bcv - tasa_base_comparar, 4) if tasa_base_comparar > 0 else 0.0

    if diferencia > 0:
        texto_tendencia = f"{e('SUBIDA', '📈')} BCV AUMENTÓ {abs(diferencia):.2f} BS PARA SU FECHA VALOR BCV {e('CALENDARIO', '📅')}"
    elif diferencia < 0:
        texto_tendencia = f"{e('BAJADA', '📉')} BCV BAJÓ {abs(diferencia):.2f} BS PARA SU FECHA VALOR BCV {e('CALENDARIO', '📅')}"
    else:
        texto_tendencia = f"{e('BALANZA', '⚖️')} BCV MANTIENE SU TASA PARA SU FECHA VALOR BCV {e('CALENDARIO', '📅')}"

    tasa_intervencion = tasa_bcv * (1 + (porcentaje / 100))

    texto = (
        f"{e('MONITOR', '🖥️')} <b>¿Cuántos bolívares necesitas para comprar en Intervención?</b>\n\n"
        f"<blockquote>{e('CALENDARIO', '📅')} <b>Fecha Valor BCV:</b> {fecha_valor_bcv}</blockquote>\n"
        f"<blockquote>{texto_tendencia}</blockquote>\n"
        f"<blockquote>{e('BCV', '🏛️')} <b>BCV Oficial:</b> <code>{tasa_bcv:.3f}</code> Bs</blockquote>\n"
        f"<blockquote>{e('BALANZA', '⚖️')} <b>BCV + {porcentaje_txt}:</b> <code>{tasa_intervencion:.3f}</code> Bs ({porcentaje_txt})</blockquote>\n"
        f"----------------------------------------\n\n"
    )

    for monto_usd in range(100, 1100, 100):
        monto_bs = monto_usd * tasa_intervencion
        texto += f"{e('DINERO', '💵')} <b>{monto_usd} USD:</b> {e('FLECHA_DERECHA', '➡️')} Bs: <code>{monto_bs:,.0f}</code>\n"

    return texto
    
    
# ==========================================
#     MANEJADORES DE COMANDOS Y BOTONES
# ========================================== 

# Manejador para borrar teclado / Menu desplegable en el grupo para administrador
@bot.message_handler(commands=['borrar_teclado'])
def borrar_teclado(message):
    bot.reply_to(message, "Limpiando teclado...", reply_markup=types.ReplyKeyboardRemove())
    

# Manejador para ejecutar /tasas en grupos permitidos y privados
@bot.message_handler(commands=['tasas', 'tasa'])
def handle_tasas_comando(message):
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id

    # --- FILTRO DE SEGURIDAD GENERAL ---
    if not es_chat_permitido(bot, message, CHATS_PERMITIDOS, USUARIOS_AUTORIZADOS, CREADOR_ID):
        return

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

        try:
            texto_resultado = construir_monitor_canal_html()
            markup_tasas = InlineKeyboardMarkup()
            markup_tasas.add(InlineKeyboardButton("🔄 Actualizar Tasas", callback_data="refrescar_canal_tasas"))

            enviar_o_reemplazar_privado(chat_id, user_id, texto_resultado, reply_markup=markup_tasas)
            return
        except Exception as e:
            print(f"Error en tasas privado: {e}")
            bot.send_message(chat_id, "❌ Error temporal al obtener tasas. Inténtalo de nuevo en unos segundos.")
            return

    # --- 2. EN GRUPOS ---
    if getattr(message, 'is_automatic_forward', False):
        try:
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=message.message_id, reply_markup=None)
        except Exception:
            pass
        return

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
            markup_tasas = None

            if str(chat_id) == str(CANAL_PRUEBA):
                markup_tasas = InlineKeyboardMarkup()
                markup_tasas.row(
                    InlineKeyboardButton("🔄 Actualizar Tasas", callback_data="refrescar_canal_tasas"),
                    InlineKeyboardButton("🗑️ Borrar", callback_data="borrar_mensaje")
                )

            msg_enviado = bot.send_message(
                chat_id,
                construir_monitor_canal_html(),
                parse_mode="HTML",
                reply_markup=markup_tasas
            )

            borrar_mensaje_luego(chat_id, msg_enviado.message_id, TIEMPO_VIDA_TABLA)

        except Exception as e:
            print(f"Error enviando tasas en grupo: {e}")

    else:
        ahora = time.time()
        ultima_vez_aviso = grupos_tiempo_aviso.get(chat_id, 0)

        if ahora - ultima_vez_aviso > RATE_LIMIT_AVISO:
            try:
                aviso = bot.send_message(
                    chat_id,
                    f"❌ <b>Comando exclusivo para Administradores.</b>\n\n"
                    f"Hola @{message.from_user.username or message.from_user.first_name}. Para mantener el orden, "
                    f"👉 Consulta todas las tasas libremente en mi chat privado: @{BOT_USERNAME}",
                    parse_mode="HTML"
                )
                grupos_tiempo_aviso[chat_id] = ahora
                borrar_mensaje_luego(chat_id, aviso.message_id, 10)
            except Exception:
                pass

# Manejador para ejecutar /zinli en grupos permitidos y privados
@bot.message_handler(commands=['zinli'])
def handle_zinli_comando(message):
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id

    # --- FILTRO DE SEGURIDAD GENERAL ---
    if not es_chat_permitido(bot, message, CHATS_PERMITIDOS, USUARIOS_AUTORIZADOS, CREADOR_ID):
        return

    # --- 1. CHAT PRIVADO ---
    if message.chat.type == 'private':
        if message.text and message.text.strip().startswith('/'):
            try:
                bot.delete_message(chat_id, message.message_id)
            except Exception:
                pass

        if not usuario_esta_unido(user_id):
            bot.reply_to(message, "❌ No tienes acceso. Debes unirte al canal oficial para usar el bot.")
            return

        try:
            texto_resultado = construir_monitor_zinli_html()
            markup_tasas = InlineKeyboardMarkup()
            markup_tasas.add(InlineKeyboardButton("🔄 Actualizar Tasas", callback_data="refrescar_canal_zinli"))

            enviar_o_reemplazar_privado(chat_id, user_id, texto_resultado, reply_markup=markup_tasas)
            return
        except Exception as e:
            print(f"Error en zinli privado: {e}")
            bot.send_message(chat_id, "❌ Error temporal al obtener tasas. Inténtalo de nuevo en unos segundos.")
            return

    # --- 2. EN GRUPOS ---
    if getattr(message, 'is_automatic_forward', False):
        try:
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=message.message_id, reply_markup=None)
        except Exception:
            pass
        return

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
            markup_tasas = None

            if str(chat_id) == str(CANAL_PRUEBA):
                markup_tasas = InlineKeyboardMarkup()
                markup_tasas.row(
                    InlineKeyboardButton("🔄 Actualizar Tasas", callback_data="refrescar_canal_zinli"),
                    InlineKeyboardButton("🗑️ Borrar", callback_data="borrar_mensaje")
                )

            msg_enviado = bot.send_message(
                chat_id,
                construir_monitor_zinli_html(),
                parse_mode="HTML",
                reply_markup=markup_tasas
            )

            borrar_mensaje_luego(chat_id, msg_enviado.message_id, TIEMPO_VIDA_TABLA)

        except Exception as e:
            print(f"Error enviando tasas zinli en grupo: {e}")

    else:
        ahora = time.time()
        ultima_vez_aviso = grupos_tiempo_aviso.get(chat_id, 0)

        if ahora - ultima_vez_aviso > RATE_LIMIT_AVISO:
            try:
                aviso = bot.send_message(
                    chat_id,
                    f"❌ <b>Comando exclusivo para Administradores.</b>\n\n"
                    f"Hola @{message.from_user.username or message.from_user.first_name}. Para mantener el orden, "
                    f"📌 Consulta todas las tasas libremente en mi chat privado: @{BOT_USERNAME}",
                    parse_mode="HTML"
                )
                grupos_tiempo_aviso[chat_id] = ahora
                borrar_mensaje_luego(chat_id, aviso.message_id, 10)
            except Exception:
                pass
                


# Manejador para /p y el botón P2P
@bot.message_handler(commands=['p', 'p2p'])
@bot.message_handler(func=lambda m: m.text and m.text.strip() == "🟢☠️ Precio-Usdt ☠️🔴")
def handle_precio_comando(message):
    procesar_precio(message)

# Manejador para el botón de Intervención y el comando /i
@bot.message_handler(commands=['i'])
@bot.message_handler(func=lambda m: m.text and m.text.strip() == "📊📊 Intervencion 📊📊")
def handle_intervencion_comando(message):
    procesar_intervencion(message)

# Manejador para los comandos /bp y /gp
@bot.message_handler(commands=['bp', 'gp'])
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
            f"<blockquote>{e('ROBOTICO', '👏🏼')} <b>¡Aprovecha al máximo las herramientas del Bot!</b> </blockquote>\n\n"
            f"{e( 'CONSULTA1', '💾')} Consulta en privado {e( 'ESCUDO', '🛡')} , sin límites y sin esperar {e( 'RELOJERA', '⏱')} tiempos de enfriamiento:\n"
            f"<blockquote>{e('MONITOR', '💻')} Monitor ~ {e('USDT', '🪙')} P2P / {e('CALENDARIO', '🗓')} BCV en tiempo real</blockquote>\n"
            f"{e( 'CALCULADORA', '🧮')} Calculadora 🇻🇪 BS y {e('DINERO', '💵')} USD / {e('BCV', '🏦')} Intervención\n"
            f"{e( 'GUIAS', '🖥️')} Guías paso a paso\n\n"
            f"<blockquote>{e('CHINCHE', '📌')} <b>Toca aquí para iniciar:</b> @BancoIDV_bot</blockquote>\n"
            f"-----------------------------------------\n\n"
        )
        
        msg_inv = bot.send_message(message.chat.id, texto_invitacion, parse_mode="HTML")
        # El aviso de invitación se borra a los 3 minutos (180 seg) para no hacer basura
        borrar_mensaje_luego(message.chat.id, msg_inv.message_id, 180)

    else:
        # 3. Si no es autorizado (usuario normal u otro admin), desintegra el aviso en 5 segundos
        aviso = bot.send_message(
            message.chat.id,
            f'👮🏼‍♀️ <b>Comando exclusivo de los administradores principales:</b>\n'
            f'✨ <a href="tg://user?id=5073264705">Enderson</a>\n'
            f'⭐ <a href="tg://user?id=791436853">Sarita</a>',
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        borrar_mensaje_luego(message.chat.id, aviso.message_id, 15)
                            
        
@bot.message_handler(func=lambda message: message.chat.type == "private" and message.text in [
    "🟢 P2P-USDT 🔴",
    "📊 Intervencion 📊",
    "📟 Calculadora",
    "📜 Regla de Oro 📜",
    "🔶 BPay 🔶",
    "🔷 GPay 🔷",
    "⚙️ Soporte",
    "🤖 IA Consulta"
])
def handle_botones_menu(message):
    if message.text == "🟢 P2P-USDT 🔴":
        procesar_precio(message)
    elif message.text == "📊 Intervencion 📊":
        procesar_intervencion(message)
    elif message.text == "📟 Calculadora":
        solicitar_calculadora(message)
    elif message.text == "📜 Regla de Oro 📜":
        procesar_regla_oro(message)
    elif message.text in ["🔶 BPay 🔶", "🔷 GPay 🔷"]:
        procesar_guias(message)
    elif message.text == "⚙️ Soporte":
        procesar_soporte(message)
    elif message.text == "🤖 IA Consulta":
        solicitar_ia_consulta(message)
                     
# ==========================================
# REEMPLAZO LIMPIO PARA CHAT PRIVADO
# ==========================================
ultimos_mensajes_privados = {}

def enviar_o_reemplazar_privado(chat_id, user_id, texto, reply_markup=None):
    """Envia un nuevo mensaje directo en chat privado de forma rapida y sin latencia."""
    try:
        # Intento 1: Enviar con formato HTML
        return bot.send_message(
            chat_id,
            texto,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    except Exception as e:
        print(f"⚠️ Falló el envío HTML (Error 400), enviando texto plano: {e}")
        # Intento 2 (Fallback): Si el HTML falla, envia sin parse_mode para no romper
        return bot.send_message(
            chat_id,
            texto,
            reply_markup=reply_markup
        )
            
# ==========================================
#  LÓGICA CON AUTODESTRUCCIÓN Y LIMPIEZA
# ==========================================

def procesar_precio(message):
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id

    # Permite el paso ÚNICAMENTE si el chat está permitido por las reglas de seguridad 
    if not es_chat_permitido(bot, message, CHATS_PERMITIDOS, USUARIOS_AUTORIZADOS, CREADOR_ID):
        return

    # --- 1. CHAT PRIVADO ---
    if message.chat.type == "private":
        if message.text and message.text.strip().startswith('/'):
            try:
                bot.delete_message(chat_id, message.message_id)
            except Exception:
                pass

        if not usuario_esta_unido(user_id):
            bot.reply_to(message, "❌ No tienes acceso. Debes solitar unirte al grupo de charla 👉🏼 @COMUNIDV , ↪️ volver al bot, ✏️ escribir /start , resolver el captcha ✅🔍 e ingresar al grupo.")
            return

        try:
            monitor_base = construir_monitor_texto_html()
            
            if es_admin_vip(bot, message.from_user):
                texto_completo = monitor_base
            else:
                aviso_regla = "\n\n💡 <b>¿Quieres saber cómo calcular tus ganancias paso a paso?</b>\n Presiona el botón <b>📜 Regla de Oro 📜</b> en el menú de abajo. 👇👇"
                texto_completo = monitor_base + aviso_regla

            markup_tasas = InlineKeyboardMarkup()
            markup_tasas.add(InlineKeyboardButton("🔄 Actualizar Tasas", callback_data="refrescar_tasas"))

            enviar_o_reemplazar_privado(chat_id, user_id, texto_completo, reply_markup=markup_tasas)
            return

        except Exception as e:
            print(f"Error en precio privado: {e}")
            bot.send_message(chat_id, "❌ Error temporal al obtener tasas. Inténtalo de nuevo en unos segundos.")
            return
            
    # --- 2. EN GRUPOS ---
    # Si el mensaje proviene de un reenvío automático del canal al grupo:
    if getattr(message, 'is_automatic_forward', False):
        try:
            # Quitamos los botones inline en la copia del grupo
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=message.message_id, reply_markup=None)
        except Exception:
            pass
        return  # Frenamos la ejecución para que no responda con errores de Admin


    # --- 2. EN GRUPOS ---
    # Borramos el comando ejecutado inmediatamente para mantener el chat limpio
    try:
        bot.delete_message(chat_id, message.message_id)
    except Exception:
        pass

    # SOLO si es CREADOR, ADMIN VIP o ADMIN DEL CANAL responde:
    if str(user_id) == str(CREADOR_ID) or es_admin_vip(bot, message.from_user) or es_administrador(bot, chat_id, user_id, message.from_user):
        try:
            markup_precio = None

            # Si estamos en el grupo cerrado de admins, agregamos los botones de refrescar/borrar
            if str(chat_id) == str(CANAL_PRUEBA):
                markup_precio = InlineKeyboardMarkup()
                markup_precio.row(
                    InlineKeyboardButton("🔄 Actualizar Tasas", callback_data="refrescar_tasas"),
                    InlineKeyboardButton("🗑️ Borrar", callback_data="borrar_mensaje")
                )

            # Enviamos la tabla
            msg_enviado = bot.send_message(
                chat_id,
                construir_monitor_texto_html(),
                parse_mode="HTML",
                reply_markup=markup_precio
            )

            # Autodestrucción del mensaje enviado tras X minutos
            borrar_mensaje_luego(chat_id, msg_enviado.message_id, TIEMPO_VIDA_TABLA)

        except Exception as e:
            print(f"Error enviando precio en grupo: {e}")


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
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id

    # --- FILTRO DE SEGURIDAD GENERAL ---
    # Permite el paso ÚNICAMENTE si el chat está permitido en las reglas de seguridad 
    if not es_chat_permitido(bot, message, CHATS_PERMITIDOS, USUARIOS_AUTORIZADOS, CREADOR_ID):
        return

    # --- 1. CHAT PRIVADO ---
    if message.chat.type == "private":
        # ORDEN DE MANDO: Borra el comando enviado por el usuario si empieza con '/'
        if message.text and message.text.strip().startswith('/'):
            try:
                bot.delete_message(chat_id, message.message_id)
            except Exception:
                pass

        if not usuario_esta_unido(user_id):
            bot.reply_to(message, "❌ No tienes acceso. Debes solicitar unirte al grupo de charla 👉🏼 @COMUNIDV , ↪️ volver al bot, ✏️ escribír /start , resolver el captcha ✅🔍 e ingresar al grupo.")
            return

        # Creamos el botón flotante para actualizar
        markup_intervencion = InlineKeyboardMarkup()
        markup_intervencion.add(InlineKeyboardButton("🔄 Actualizar Cálculo", callback_data="refrescar_intervencion"))

        # EVALUACIÓN DE EXCEPCIÓN 1%:
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
    # Si el mensaje proviene de un reenvío automático del canal al grupo:
    if getattr(message, 'is_automatic_forward', False):
        try:
            # Quitamos los botones inline en la copia del grupo
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=message.message_id, reply_markup=None)
        except Exception:
            pass
        return  # Frenamos la ejecución para que no responda con errores de Admin
        

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

    # Verificación de permisos para responder en grupo
    if str(user_id) == str(CREADOR_ID) or es_admin_vip(bot, message.from_user) or es_admin_g:
        try:
            # EVALUACIÓN DE EXCEPCIÓN EN GRUPOS PARA PORCENTAJE (1.0% vs 0.5%)
            if es_admin_especial(message.from_user):
                texto_grupo = construir_intervencion_texto_html(user=message.from_user, porcentaje=1.0)
            else:
                texto_grupo = construir_intervencion_texto_html(user=message.from_user, porcentaje=0.5)

            # SOLO si estamos en el grupo de admins, creamos los 2 botones VIP
            if str(chat_id) == str(CANAL_PRUEBA):
                markup_intervencion = InlineKeyboardMarkup()
                markup_intervencion.row(
                    InlineKeyboardButton("🔄 Actualizar Cálculo", callback_data="refrescar_intervencion"),
                    InlineKeyboardButton("🗑️ Borrar", callback_data="borrar_mensaje")
                )
            else:
                markup_intervencion = None

            # ENVIAMOS EL MENSAJE (Se envía en TODOS los grupos donde seas Admin/Propietario)
            msg_enviado = bot.send_message(
                chat_id,
                texto_grupo,
                parse_mode="HTML",
                reply_markup=markup_intervencion  # Será None en grupos normales, y con botones en Admin
            )

            # Autodestrucción del mensaje
            borrar_mensaje_luego(chat_id, msg_enviado.message_id, TIEMPO_VIDA_TABLA)

        except Exception as e:
            print(f"Error enviando intervencion en grupo: {e}")

    else:
        # Si un usuario común intenta usarlo en el grupo, aplica el Rate Limit de aviso
        ahora = time.time()
        ultima_vez_aviso = grupos_tiempo_aviso.get(chat_id, 0)

        if ahora - ultima_vez_aviso > RATE_LIMIT_AVISO:
            try:
                aviso = bot.send_message(
                    chat_id,
                    f"❌ <b>Comando exclusivo para Administradores.</b>\n\n"
                    f"Hola @{message.from_user.username or message.from_user.first_name}. Para mantener el orden, este comando solo puede ser ejecutado por administradores.\n"
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
            bot.reply_to(message, "❌ No tienes acceso. Debes solicitar unirte al grupo de charla 👉🏼 @COMUNIDV , ↪️ volver al bot, ✏️ escribir  /start , resolver el captcha ✅🔍 e ingresar al grupo.")
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
            bot.reply_to(message, "❌ No tienes acceso. Debes solicitar unirte al grupo de charla 👉🏼 @COMUNIDV , ↪️ volver al bot, ✏️ escribir  /start , resolver el captcha ✅🔍 e ingresar al grupo.")
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
            bot.reply_to(message, "❌ No tienes acceso. Debes solicitar unirte al grupo de charla 👉🏼 @COMUNIDV , ↪️ volver al bot , ✏️ escribir /start , resolver el captcha ✅🔍 e ingresar al grupo.")
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

@bot.callback_query_handler(func=lambda call: call.data == "refrescar_canal_tasas")
def refrescar_canal_tasas_callback(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id if call.from_user else None

    # 🚨 BLINDAJE EN GRUPOS Y CANALES
    if call.message.chat.type != "private":
        es_admin_o_vip = (
            str(user_id) == str(CREADOR_ID) 
            or es_admin_vip(bot, call.from_user) 
            or es_administrador(bot, chat_id, user_id, call.from_user)
        )
        if not es_admin_o_vip:
            bot.answer_callback_query(
                call.id,
                text=f"❌ Solo Administradores pueden actualizar la tasa aquí.👉 Usa mi chat privado: @{BOT_USERNAME}",
                show_alert=True
            )
            return

    # Si es Admin o es en un grupo/privado, se ejecuta la actualización normal:
    texto_resultado = construir_monitor_canal_html()

    markup = InlineKeyboardMarkup()
    if str(chat_id) == str(CANAL_PRUEBA):
        markup.row(
            InlineKeyboardButton("🔄 Actualizar Tasas", callback_data="refrescar_canal_tasas"),
            InlineKeyboardButton("🗑️ Borrar", callback_data="borrar_mensaje")
        )
    else:
        markup.add(InlineKeyboardButton("🔄 Actualizar Tasas", callback_data="refrescar_canal_tasas"))

    try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=texto_resultado,
            parse_mode="HTML",
            reply_markup=markup
        )
        bot.answer_callback_query(call.id, "✅ Tasas actualizadas")
    except Exception:
        bot.answer_callback_query(call.id, "Las tasas ya están al día")



@bot.callback_query_handler(func=lambda call: call.data == "refrescar_canal_zinli")
def refrescar_canal_zinli_callback(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id if call.from_user else None

    # 🚨 BLINDAJE EN GRUPOS Y CANALES
    if call.message.chat.type != "private":
        es_admin_o_vip = (
            str(user_id) == str(CREADOR_ID)
            or es_admin_vip(bot, call.from_user)
            or es_administrador(bot, chat_id, user_id, call.from_user)
        )
        if not es_admin_o_vip:
            bot.answer_callback_query(
                call.id,
                text=f"❌ Solo Administradores pueden actualizar la tasa aquí.👉 Usa mi chat privado: @{BOT_USERNAME}",
                show_alert=True
            )
            return

    # Si es Admin o es en privado, se ejecuta la actualización normal:
    texto_resultado = construir_monitor_zinli_html()

    markup = InlineKeyboardMarkup()
    if str(chat_id) == str(CANAL_PRUEBA):
        markup.row(
            InlineKeyboardButton("🔄 Actualizar Tasas", callback_data="refrescar_canal_zinli"),
            InlineKeyboardButton("🗑️ Borrar", callback_data="borrar_mensaje")
        )
    else:
        markup.add(InlineKeyboardButton("🔄 Actualizar Tasas", callback_data="refrescar_canal_zinli"))

    try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=texto_resultado,
            parse_mode="HTML",
            reply_markup=markup
        )
        bot.answer_callback_query(call.id, "🔄 Tasas actualizadas")
    except Exception:
        bot.answer_callback_query(call.id, "Las tasas ya están al día")
        
    
# ==========================================
#    MANEJADOR DEL BOTÓN INLINE (REFRESCAR)
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data == "refrescar_tasas")
def callback_refrescar_tasas(call):
    user_id = call.from_user.id if call.from_user else None

    # 🚨 1. BLINDAJE EN GRUPOS Y CANALES
    if call.message.chat.type != "private":
        es_admin_o_vip = (
            str(user_id) == str(CREADOR_ID) 
            or es_admin_vip(bot, call.from_user) 
            or es_administrador(bot, call.message.chat.id, user_id, call.from_user)
        )
        if not es_admin_o_vip:
            bot.answer_callback_query(
                call.id,
                text=f"❌ Solo Administradores pueden actualizar la tasa en el grupo.👉 Consulta libremente en privado: @{BOT_USERNAME}",
                show_alert=True
            )
            return

    # 2. Verificación de usuario unido para Privados / Grupos
    if not usuario_esta_unido(user_id):
        bot.answer_callback_query(call.id, text="❌ Acceso denegado. No perteneces al canal.")
        return

    # 3. Responder de inmediato al botón
    bot.answer_callback_query(call.id, text="🔄 Actualizando tasas en vivo...")

    try:
        # 4. Forzamos la actualización desde Binance
        refrescar_tasas_en_vivo()
        monitor_fresco = construir_monitor_texto_html()

        aviso_regla = (
            "\n\n 💡<b>¿Quieres saber cómo calcular tus ganancias paso a paso?</b>\n"
            "Presiona el botón <b>📜 Regla de Oro 📜</b> en el menú de abajo. 👇👇"
        )

        if es_admin_vip(bot, call.from_user) or call.message.chat.type == "channel":
            texto_editado = monitor_fresco
        else:
            texto_editado = monitor_fresco + aviso_regla

        # 5. Construimos el teclado
        markup_tasas = InlineKeyboardMarkup()
        if str(call.message.chat.id) == str(CANAL_PRUEBA) or es_admin_vip(bot, call.from_user):
            markup_tasas.row(
                InlineKeyboardButton("🔄 Actualizar Tasas", callback_data="refrescar_tasas"),
                InlineKeyboardButton("🗑️ Borrar", callback_data="borrar_mensaje")
            )
        else:
            markup_tasas.add(InlineKeyboardButton("🔄 Actualizar Tasas", callback_data="refrescar_tasas"))

        # 6. Editamos el mensaje
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
    user_id = call.from_user.id if call.from_user else None

    # 🚨 1. BLINDAJE EN GRUPOS Y CANALES
    if call.message.chat.type != "private":
        es_admin_o_vip = (
            str(user_id) == str(CREADOR_ID) 
            or es_admin_vip(bot, call.from_user) 
            or es_administrador(bot, call.message.chat.id, user_id, call.from_user)
        )
        if not es_admin_o_vip:
            bot.answer_callback_query(
                call.id,
                text=f"❌ Solo Administradores pueden actualizar la intervención aquí.👉 Consulta libremente en privado: @{BOT_USERNAME}",
                show_alert=True
            )
            return

    # 2. Verificación de usuario unido
    if not usuario_esta_unido(user_id):
        bot.answer_callback_query(call.id, text="❌ Acceso denegado. No perteneces al canal.")
        return

    try:
        texto_fresco = construir_intervencion_texto_html(call.from_user)

        # Construimos el teclado evaluando si está en el grupo de admins
        markup_intervencion = InlineKeyboardMarkup()
        if str(call.message.chat.id) == str(CANAL_PRUEBA) or es_admin_vip(bot, call.from_user):
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
        bot.answer_callback_query(call.id, text="Las tasas se mantienen actualizadas. 🏛️")
        
                    
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
        if self.path == '/actualizar_bcv':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)

            try:
                datos = json.loads(post_data.decode('utf-8'))
                clave = datos.get("clave")
                tasa = datos.get("tasa")
                fecha = datos.get("fecha")

                if clave != CLAVE_SECRETA_BCV:
                    self.send_response(403)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.send_wfile.write(b'{"status": "error", "message": "No autorizado"}')
                    return

                if tasa and fecha and r:
                    tasa_nueva = float(tasa)
                    fecha_nueva = str(fecha).strip()

                    # Lectura del diccionario centralizado de Redis
                    datos_bcv = obtener_datos_bcv_validos()
                    
                    tasa_hoy_actual = datos_bcv.get("tasa_hoy", 0.0)
                    fecha_hoy_actual = datos_bcv.get("fecha_hoy", "")

                    # ROTACIÓN ESTRUCTURADA:
                    # Si la fecha que entra es distinta a la fecha de hoy, la de hoy pasa a ser "anterior" (Viernes)
                    # y la nueva entra como "mañana" (Lunes).
                    if fecha_nueva != fecha_hoy_actual:
                        if tasa_hoy_actual > 0:
                            datos_bcv["tasa_anterior"] = tasa_hoy_actual
                            datos_bcv["fecha_anterior"] = fecha_hoy_actual
                        
                        datos_bcv["tasa_manana"] = tasa_nueva
                        datos_bcv["fecha_manana"] = fecha_nueva
                    else:
                        # Si es la misma fecha del día, actualiza tasa_hoy directamente
                        datos_bcv["tasa_hoy"] = tasa_nueva
                        datos_bcv["fecha_hoy"] = fecha_nueva

                    # Guardar el diccionario completo actualizado en Redis
                    r.set("bcv_datos", json.dumps(datos_bcv))

                    print(f"🔥 [WEBHOOK] Tasa recibida y guardada en Redis: {tasa_nueva} | Fecha: {fecha_nueva}")

                    # Envío inmediato de reportes a canales
                    def enviar_reportes_sincronizados():
                        try:
                            canales_destino = [CANAL_PRUEBA, CANAL_SECUNDARIO]
                            texto_intervencion = construir_intervencion_texto_html()
                            for canal in canales_destino:
                                if canal:
                                    try:
                                        bot.send_message(canal, texto_intervencion, parse_mode="HTML")
                                    except Exception as e_canal:
                                        print(f"⚠️ No se pudo enviar Intervención a {canal}: {e_canal}")

                            time.sleep(5)
                            texto_monitor = construir_monitor_texto_html()
                            for canal in canales_destino:
                                if canal:
                                    try:
                                        bot.send_message(canal, texto_monitor, parse_mode="HTML")
                                    except Exception as e_canal:
                                        print(f"⚠️ No se pudo enviar Monitor a {canal}: {e_canal}")
                        except Exception as e:
                            print(f"⚠️ Error enviando reportes automáticos: {e}")

                    threading.Thread(target=enviar_reportes_sincronizados, daemon=True).start()

                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.send_wfile.write(b'{"status": "success", "message": "Tasa procesada"}')
                else:
                    self.send_response(400)
                    self.end_headers()

            except Exception as e:
                print(f"❌ Error en Webhook: {e}")
                self.send_response(500)
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

    # Limpia webhooks y descarta actualizaciones pendientes
    try:
        bot.remove_webhook(drop_pending_updates=True)
        time.sleep(1)
    except Exception:
        pass

    # 🟢 1. Definimos los canales/grupos donde rotará el anuncio de captcha
    CHATS_ANUNCIOS = [CANAL_PRUEBA]

    # 🟢 2. Activamos el ciclo de anuncios pasando bot y la lista de chats
    iniciar_modulo_anuncios(bot, CHATS_ANUNCIOS)

    print("🚀 Bot Maestro en línea con limpieza automática y temporizador de 5 min...")

    # Inicia el receptor webhook en segundo plano
    threading.Thread(target=iniciar_servidor_receptor, daemon=True).start()

    # Arranca el polling limpio
    bot.infinity_polling()
    

    
