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
from telebot import types
from captcha import setup_verification_handlers
from seguridad import validar_copia_pega, es_admin_vip, es_admin_especial, es_administrador, es_chat_permitido
from seguridad import limpiar_comandos_chat, registrar_filtro_anti_raid, registrar_limpiador_servicio
from calculadora import registrar_calculadora
from ia_consulta import registrar_ia_consulta
from anuncios import iniciar_modulo_anuncios, setup_comando_aviso
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

# Canal Principal Oficial de Anuncios (Donde publica el dueño)
CANAL_CONGESTIONADO_OFICIAL = -1001504094779

# Grupo Vincular de Conversación
CANAL_CONGESTIONADO = -1001612840350

# Otros Canales/Grupos Administrativos
CANAL_ADMINS = -1003947562741
CANAL_SECUNDARIO = -1004378497075

# Canales de Pruebas (puedes mantenerlos o cambiarlos)
CANAL_PRUEBA = -1004473532809
CANAL_PRINCIPAL_IDV = -1003950050807

# USUARIOS AUTORIZADOS Y CREADOR (¡Restaurar estas líneas!)
USUARIOS_AUTORIZADOS = [5073264705, 1676933074, 6299629267, 8166481937]
CREADOR_ID = 5073264705

# 🟢 REGISTRAR COMANDOS PRIORITARIOS AQUÍ (Arriba de los demás handlers)
setup_comando_aviso(bot, es_admin_vip, USUARIOS_AUTORIZADOS)

# Lista unificada de chats donde el bot responderá a comandos de canal (/p, /i, /tasas)
CHATS_PERMITIDOS = [
    CANAL_CONGESTIONADO_OFICIAL, # <-- ID del canal principal
    CANAL_CONGESTIONADO,         # <-- Grupo vinculado
    CANAL_ADMINS, 
    CANAL_PRINCIPAL_IDV, 
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
        markup.add(KeyboardButton("🤖 IA Consulta"))
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

    markup.add(btn_precio, btn_intervencion)
    markup.add(btn_regla, btn_calculadora)
    markup.add(btn_bpay, btn_gpay)
    markup.add(btn_soporte)
    markup.add(btn_ia)
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
    "👋 <b>¡Bienvenido al Monitor Oficial IDV ~ Arbitraje P2P!</b>\n\n"
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


# ===============================================
# DESPACHADOR DE MENÚ Y CAPTCHA
# ===============================================

def enviar_menu_principal(bot, user, chat_id):
    if es_admin_vip(bot, user):
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(KeyboardButton("🟢 P2P-USDT 🔴"), KeyboardButton("📊 Intervencion 📊"))
        markup.add(KeyboardButton("📟 Calculadora"), KeyboardButton("⚙️ Soporte"))
        markup.add(KeyboardButton("🤖 IA Consulta"))
        
        texto_vip = (
            f"<b>👑 ¡Hola, {user.first_name}!</b>\n\n"
            f"Gracias por tu valiosa labor diaria manteniendo el orden en la comunidad - AntonyS4.\n"
            f"<i>⚡ Tienes activo el entorno VIP de trabajo rápido (sin distracciones ni guías de inicio).</i>"
        )
        bot.send_message(chat_id, texto_vip, parse_mode="HTML", reply_markup=markup)
    else:
        markup = obtener_teclado_privado(user)
        bot.send_message(chat_id, TEXTO_START, parse_mode="HTML", reply_markup=markup)


# Inicialización del captcha
setup_verification_handlers(
    bot, 
    [CANAL_PRUEBA, CANAL_CONGESTIONADO],
    funcion_menu=enviar_menu_principal, 
    funcion_esta_unido=usuario_esta_unido
)

    
    # Actualizacion de velocidad
def obtener_datos_bcv_validos():
    """Retorna la tasa y fecha actuales guardadas en memoria desde el Cazador BCV."""
    tasa = CACHE_TASAS.get("bcv_tasa", 756.71)
    fecha = CACHE_TASAS.get("bcv_fecha", "2026-08-06")
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
                    
# --- CACHÉ GLOBAL DE TASAS ---
CACHE_TASAS = {
    "bcv_tasa": 756.71,
    "bcv_tasa_anterior": 755.90,
    "bcv_fecha": "2026-08-06",
    "rangos": {} # Guardará las tasas calculadas por rango
}

# Registramos el módulo pasándole la instancia del bot y la función para leer CACHE_TASAS
solicitar_calculadora = registrar_calculadora(bot, lambda: CACHE_TASAS, obtener_teclado_privado)

# --- PERSISTENCIA EN REDIS ---

def guardar_cache_en_disco():
    try:
        if r:
            r.set("CACHE_TASAS_STORAGE", json.dumps(CACHE_TASAS))
            print("💾 ¡Cache guardada exitosamente en Redis!")
    except Exception as e:
        print(f"Error guardando caché en Redis: {e}")


def cargar_cache_de_disco():
    global CACHE_TASAS
    try:
        if r:
            data = r.get("CACHE_TASAS_STORAGE")
            if data:
                CACHE_TASAS.update(json.loads(data))
                print("💾 ¡Tasas recuperadas con éxito desde Redis!")
    except Exception as e:
        print(f"Error leyendo caché desde Redis: {e}")
            
def actualizar_cache_segundo_plano():
    global CACHE_TASAS
    while True:
        try:
            # Leemos la tasa BCV actual almacenada en memoria (la que envía el cazador)
            tasa_bcv = CACHE_TASAS.get("bcv_tasa", 756.71)
            tasa_bcv_ajustada = tasa_bcv * 1.005

            ranges_def = [
                ("Rango Menor ($50 - $100)", 50.0),
                ("Rango Medio ($100 - $300)", 150.0),
                ("Rango Mayor ($500+)", 500.0),
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

            CACHE_TASAS["rangos"] = nuevos_rangos
            guardar_cache_en_disco()  # 👈 AGREGA ESTA LÍNEA AQUÍ (alrededor de la línea 311)

        except Exception as e:
            print(f"Error actualizando caché: {e}")

        time.sleep(60)
        
threading.Thread(target=actualizar_cache_segundo_plano, daemon=True).start()

def refrescar_tasas_en_vivo():
    global CACHE_TASAS
    tasa_bcv = CACHE_TASAS.get("bcv_tasa", 756.71)
    fecha_bcv = CACHE_TASAS.get("bcv_fecha", "2026-08-06")

    tasa_bcv_ajustada = tasa_bcv * 1.005
    rangos_def = [
        ("Rango Menor ($50 - $100)", 50.0),
        ("Rango Medio ($100 - $300)", 150.0),
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
        nuevos_rangos[str(usd_ref)] = {
            "nombre": nombre,
            "compra": compra,
            "venta": venta
        }

    CACHE_TASAS["rangos"] = nuevos_rangos


# DICCIONARIO DE EMOJIS ANIMADOS DE TELEGRAM (IDs)
TG_EMOJIS = {
    "MONITOR": "5193177581888755275",      # 💻 / 😀
    "CALENDARIO": "5413879192267805083",   # 🗓
    "BCV": "5183805009766123191",          # 🏦 (Logo BCV)
    "BALANZA": "5400250414929041085",      # ⚖️
    "ETIQUETA": "5222444124698853913",     # 🔖
    "BOMBILLA": "5262844652964303985",     # 💡
    "CHINCHE": "5397782960512444700",      # 📌
    "RANGO_1": "5440539497383087970",      # 🥇 (Oro)
    "RANGO_2": "5447203607294265305",      # 🥈 (Plata)
    "RANGO_3": "5453902265922376865",      # 🥉 (Bronce)
    "USDT": "5814556334829343625",         # 🪙 (Logo USDT)
    "VERDE": "5416081784641168838",        # 🟢 (Compra)
    "ROJO": "5411225014148014586",         # 🔴 (Venta)
    "SUBIDA": "5244837092042750681",       # 📈
    "BAJADA": "5246762912428603768",       # 📉
    "MUNDO": "5224450179368767019",        # 🌎
    "FLECHA_DERECHA": "5416117059207572332", # ➡️
    "DINERO": "5197434882321567830",        # 💵
    "BINANCE_P2P": "5832421268476924783"    # 🪙
}

def e(key, fallback=""):
    emoji_id = TG_EMOJIS.get(key, "")
    if emoji_id:
        return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
    return fallback

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
    tasa_bcv = CACHE_TASAS.get("bcv_tasa", 756.71)
    fecha_valor_bcv = CACHE_TASAS.get("bcv_fecha", "06 Agosto 2026")
    tasa_intervencion = tasa_bcv * 1.005

    texto = (
        f"{e('MONITOR', '💻')} <b>Monitor de Tasas Arbitraje P2P</b>\n\n"
        f"<blockquote>{e('CALENDARIO', '🗓')} <b>Vigencia BCV :</b> {fecha_valor_bcv}</blockquote>\n"
        f"<blockquote>{e('BCV', '🏦')} <b>BCV Oficial :</b> <code>{tasa_bcv:.2f}</code> Bs</blockquote>\n"
        f"<blockquote>{e('BALANZA', '⚖️')} <b>BCV + 0.5% :</b> <code>{tasa_intervencion:.2f}</code> Bs</blockquote>\n\n"
        f"{e('ETIQUETA', '🔖')} <b>Filtros Activos:</b> Verificados | Comerciables {e('BOMBILLA', '💡')} | Pago : Todos {e('CHINCHE', '📌')}\n"
        f"-----------------------------------------\n\n"
    )

    rangos_cache = CACHE_TASAS.get("rangos", {})
    
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

def construir_intervencion_texto_html(user=None, porcentaje=None):
    if porcentaje is None:
        if user and es_admin_especial(user):
            porcentaje = 1.0
        else:
            porcentaje = 0.5

    porcentaje_txt = "1%" if porcentaje == 1.0 else "0.5%"

    tasa_bcv = CACHE_TASAS.get("bcv_tasa", 756.71)
    tasa_anterior = CACHE_TASAS.get("bcv_tasa_anterior", 755.90)
    fecha_valor_bcv = CACHE_TASAS.get("bcv_fecha", "06 Agosto 2026")

    diferencia = tasa_bcv - tasa_anterior

    if diferencia > 0:
        texto_tendencia = f"{e('SUBIDA', '📈')} BCV AUMENTÓ {abs(diferencia):.2f} BS PARA SU FECHA VALOR BCV {e('CALENDARIO', '🗓')}"
    elif diferencia < 0:
        texto_tendencia = f"{e('BAJADA', '📉')} BCV BAJÓ {abs(diferencia):.2f} BS PARA SU FECHA VALOR BCV {e('CALENDARIO', '🗓')}"
    else:
        texto_tendencia = f"{e('BALANZA', '⚖️')} BCV MANTIENE SU TASA PARA SU FECHA VALOR BCV {e('CALENDARIO', '🗓')}"

    tasa_intervencion = tasa_bcv * (1 + (porcentaje / 100))

    texto = (
        f"{e('MONITOR', '💻')} <b>¿Cuántos bolívares necesitas para comprar en Intervención?</b>\n\n"
        f"<blockquote>{e('CALENDARIO', '🗓')} <b>Fecha Valor BCV:</b> {fecha_valor_bcv}</blockquote>\n"
        f"<blockquote>{texto_tendencia}</blockquote>\n"
        f"<blockquote>{e('BCV', '🏦')} <b>Tasa BCV Oficial:</b> <code>{tasa_bcv:.2f}</code> Bs</blockquote>\n"
        f"<blockquote>{e('BALANZA', '⚖️')} <b>Tasa Intervención:</b> <code>{tasa_intervencion:.2f}</code> Bs ({porcentaje_txt} Agregado)</blockquote>\n"
        f"-----------------------------------------\n\n"
    )

    for monto_usd in range(100, 1100, 100):
        monto_bs = monto_usd * tasa_intervencion
        texto += f"{e('DINERO', '💵')} <b>{monto_usd} USD</b> {e('FLECHA_DERECHA', '➡️')} Bs: <code>{monto_bs:,.0f}</code>\n"

    return texto
    
    
# ==========================================
#     MANEJADORES DE COMANDOS Y BOTONES
# ==========================================

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

            if str(chat_id) == str(CANAL_ADMINS):
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


# =======================================================
# MANEJADOR PARA PUBLICACIONES EN CANALES (/p, /i, /tasas)
# =======================================================
@bot.channel_post_handler(commands=['p', 'i', 'tasas', 'tasa'])
def manejar_post_canal(message):
    if message.chat.type != 'channel':
        return

    chat_id = message.chat.id

    if str(chat_id) in [str(c) for c in CHATS_PERMITIDOS]:
        try:
            bot.delete_message(chat_id, message.message_id)
        except Exception:
            pass

        texto_cmd = message.text.strip().lower() if message.text else ""

        if texto_cmd.startswith('/p'):
            texto_resultado = construir_monitor_texto_html()
            callback_refrescar = "refrescar_tasas"
        elif texto_cmd.startswith('/i'):
            texto_resultado = construir_intervencion_texto_html() if 'construir_intervencion_texto_html' in globals() else construir_monitor_texto_html()
            callback_refrescar = "refrescar_intervencion"
        elif texto_cmd.startswith('/tasas') or texto_cmd.startswith('/tasa'):
            texto_resultado = construir_monitor_canal_html()
            callback_refrescar = "refrescar_canal_tasas"
        else:
            return

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔄 Actualizar Tasas", callback_data=callback_refrescar))

        bot.send_message(chat_id, texto_resultado, parse_mode="HTML", reply_markup=markup)

# =============================================================
# 📢 PUBLICADOR AL CANAL CON COPY_MESSAGE (Emojis + Botones)
# =============================================================
@bot.message_handler(commands=['p_canal', 'i_canal', 'tasas_canal'])
def publicar_con_copia_canal(message):
    user_id = message.from_user.id
    user_name = f"@{message.from_user.username}" if message.from_user.username else user_id

    # 1. Filtro de seguridad para administradores
    if user_id not in USUARIOS_AUTORIZADOS and user_name not in USUARIOS_AUTORIZADOS:
        return

    # Borrar el comando escrito en el grupo
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

    cmd = message.text.strip().lower()
    callback_data_str = ""

    # 2. Seleccionar el texto y callback según el comando
    if cmd.startswith('/p_canal'):
        texto = construir_monitor_texto_html()
        callback_data_str = "refrescar_tasas"
    elif cmd.startswith('/i_canal'):
        texto = construir_intervencion_texto_html(user=message.from_user)
        callback_data_str = "refrescar_intervencion"
    elif cmd.startswith('/tasas_canal'):
        texto = construir_monitor_canal_html()
        callback_data_str = "refrescar_canal_tasas"
    else:
        return

    try:
        # Paso A: Creamos un teclado temporal para el mensaje base
        markup_base = InlineKeyboardMarkup()
        markup_base.add(InlineKeyboardButton("🔄 Actualizar", callback_data=callback_data_str))

        # Enviamos primero al grupo de administración (aquí se renderizan los tg-emojis perfectos)
        msg_grupo = bot.send_message(
            chat_id=message.chat.id,
            text=texto,
            parse_mode='HTML',
            reply_markup=markup_base
        )

        # Paso B: Preparamos los botones finales para el Canal Oficial
        markup_canal = InlineKeyboardMarkup()
        markup_canal.add(InlineKeyboardButton("🔄 Actualizar Tasas", callback_data=callback_data_str))

        # Paso C: Copiamos el mensaje exacto al Canal Principal con copy_message
        bot.copy_message(
            chat_id=CANAL_PRINCIPAL_IDV,
            from_chat_id=message.chat.id,
            message_id=msg_grupo.message_id,
            reply_markup=markup_canal
        )

        # Opcional: Notificar en el grupo
        aviso = bot.send_message(message.chat.id, "✅ <b>¡Publicado en el canal con tg-emojis y botones!</b>", parse_mode='HTML')
        borrar_mensaje_luego(message.chat.id, aviso.message_id, 4)

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ <b>Error al copiar al canal:</b> {e}", parse_mode='HTML')
        

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
            "🤖 <b>¡Aprovecha al máximo las herramientas del Bot~IDV!</b>\n\n"
            "Consulta en privado sin límites y sin esperar tiempos de enfriamiento:\n"
            "🖥️ Monitor P2P /📆 BCV en tiempo real\n"
            "📟 Calculadora e 📊 Intervención\n"
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
            f'⚠️ <b>Comando exclusivo de los administradores principales 🤓:</b>\n'
            f'• <a href="tg://user?id=5073264705">⚙️ Enderson</a>\n'
            f'• <a href="tg://user?id=1676933074">🐲 Antony</a>\n'
            f'• <a href="tg://user?id=6299629267">🐻 Oswaldo</a>\n'
            f'• <a href="tg://user?id=8166481937">👸🏼 CiIita</a>',
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        borrar_mensaje_luego(message.chat.id, aviso.message_id, 15)

# 🚨 COMANDO DE EMERGENCIA PARA CORREGIR TASA ANTERIOR
@bot.message_handler(commands=['fix_tasa'])
def fix_tasa_handler(message):
    user_id = message.from_user.id
    user_name = f"@{message.from_user.username}" if message.from_user.username else user_id
    
    if user_id in USUARIOS_AUTORIZADOS or user_name in USUARIOS_AUTORIZADOS:
        try:
            partes = message.text.split()
            if len(partes) > 1:
                tasa_fix = float(partes[1])
                CACHE_TASAS["bcv_tasa_anterior"] = tasa_fix
                guardar_cache_en_disco()
                bot.reply_to(message, f"✅ <b>¡Tasa anterior corregida a {tasa_fix}!</b>\nRAM y Redis sincronizados.", parse_mode="HTML")
            else:
                bot.reply_to(message, "⚠️ Uso: <code>/fix_tasa 755.90</code>", parse_mode="HTML")
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {e}")
        
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
            bot.reply_to(message, "❌ No tienes acceso. Debes unirte al canal oficial para usar el bot.")
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
            if str(chat_id) == str(CANAL_ADMINS):
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
            bot.reply_to(message, "❌ No tienes acceso. Debes unirte al canal oficial para usar el bot.")
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
            if str(chat_id) == str(CANAL_ADMINS):
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

@bot.callback_query_handler(func=lambda call: call.data == "refrescar_canal_tasas")
def refrescar_canal_tasas_callback(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id if call.from_user else None

    # Si se pulsa desde un CANAL PÚBLICO y NO es Creador ni Admin VIP:
    if call.message.chat.type == "channel":
        if not (str(user_id) == str(CREADOR_ID) or es_admin_vip(bot, call.from_user)):
            bot.answer_callback_query(
                call.id,
                f"❌ Solo Administradores pueden actualizar la tasa aquí.\n👉 Usa mi chat privado: @{BOT_USERNAME}",
                show_alert=True  # Alerta emergente privada
            )
            return

    # Si es Admin o es en un grupo/privado, se ejecuta la actualización normal:
    texto_resultado = construir_monitor_canal_html()

    markup = InlineKeyboardMarkup()
    if str(chat_id) == str(CANAL_ADMINS):
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
        

# ==========================================
#    MANEJADOR DEL BOTÓN INLINE (REFRESCAR)
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data == "refrescar_tasas")
def callback_refrescar_tasas(call):
    user_id = call.from_user.id if call.from_user else None

    # 🛑 1. BLINDAJE EN CANALES: Solo Creador o Admin VIP
    if call.message.chat.type == "channel":
        if not (str(user_id) == str(CREADOR_ID) or es_admin_vip(bot, call.from_user)):
            bot.answer_callback_query(
                call.id,
                text=f"❌ Solo Administradores pueden actualizar la tasa en el canal.\n👉 Consulta libremente en privado: @{BOT_USERNAME}",
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
        if str(call.message.chat.id) == str(CANAL_ADMINS) or es_admin_vip(bot, call.from_user):
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

    # 🛑 1. BLINDAJE EN CANALES: Solo Creador o Admin VIP
    if call.message.chat.type == "channel":
        if not (str(user_id) == str(CREADOR_ID) or es_admin_vip(bot, call.from_user)):
            bot.answer_callback_query(
                call.id,
                text=f"❌ Solo Administradores pueden actualizar la intervención en el canal.\n👉 Consulta libremente en privado: @{BOT_USERNAME}",
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
        if str(call.message.chat.id) == str(CANAL_ADMINS) or es_admin_vip(bot, call.from_user):
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

                    # Solo procesamos si la tasa raspada es diferente a la actual
                    if tasa_nueva != tasa_actual:
                        CACHE_TASAS["bcv_tasa_anterior"] = tasa_actual
                        CACHE_TASAS["bcv_tasa"] = tasa_nueva
                        CACHE_TASAS["bcv_fecha"] = str(fecha)

                        # Recalculamos rangos P2P inmediatamente
                        tasa_ajustada = tasa_nueva * 1.005
                        ranges_def = [
                            ("Rango Menor ($50 - $100)", 50.0),
                            ("Rango Medio ($100 - $300)", 150.0),
                            ("Rango Mayor ($500+)", 500.0),
                        ]

                        nuevos_rangos = {}
                        for nombre, usd_ref in ranges_def:
                            monto_bs = usd_ref * tasa_ajustada
                            compra = obtener_tasa_binance_p2p("BUY", monto_bs) or 0.0
                            venta = obtener_tasa_binance_p2p("SELL", monto_bs) or 0.0
                            nuevos_rangos[usd_ref] = {"nombre": nombre, "compra": compra, "venta": venta}

                        CACHE_TASAS["rangos"] = nuevos_rangos

                        # Guardamos copia física en Redis
                        guardar_cache_en_disco()
                        print(f"🔥 [WEBHOOK] Tasa BCV actualizada por El Cazador: {tasa_nueva} | Fecha: {fecha}")

                        # Anuncios automáticos sincronizados
                        def enviar_reportes_sincronizados():
                            try:
                                # Lista de canales a los que quieres enviar la notificación
                                canales_destino = [CANAL_CONGESTIONADO, CANAL_ADMINS, CANAL_SECUNDARIO]

                                # 1. Envío de Tabla de Intervención
                                texto_intervencion = construir_intervencion_texto_html()
                                for canal in canales_destino:
                                    if canal:
                                        try:
                                            bot.send_message(canal, texto_intervencion, parse_mode="HTML")
                                        except Exception as e_canal:
                                            print(f"⚠️ No se pudo enviar Intervención a {canal}: {e_canal}")
                
                                print("📢 [1/2] Tabla de Intervención enviada a los canales vía Webhook.")

                                # Pausa de 15 segundos entre avisos
                                time.sleep(15)

                                # 2. Envío de Monitor P2P
                                texto_monitor = construir_monitor_texto_html()
                                for canal in canales_destino:
                                    if canal:
                                        try:
                                            bot.send_message(canal, texto_monitor, parse_mode="HTML")
                                        except Exception as e_canal:
                                            print(f"⚠️ No se pudo enviar Monitor P2P a {canal}: {e_canal}")

                                print("📢 [2/2] Monitor P2P enviado a los canales vía Webhook.")

                            except Exception as e:
                                print(f"⚠️ Error general al publicar anuncios desde el webhook: {e}")
                

                        
                        # Se ejecuta en un hilo para responder rápido a GitHub Actions
                        threading.Thread(target=enviar_reportes_sincronizados, daemon=True).start()

                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(b'{"status":"success","message":"Tasa actualizada, guardada en Redis y anunciada"}')
                        return
                    else:
                        print(f"😴 [WEBHOOK] Tasa recibida ({tasa_nueva}) es idéntica a la actual. Sin cambios.")
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(b'{"status":"ignored","message":"Sin cambios en la tasa"}')
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
                

# =============================================================
# 🛡️ MANEJADOR INLINE (Publicaciones con Emojis Animados)
# =============================================================
@bot.inline_handler(lambda query: True)
def manejar_consultas_inline(inline_query):
    try:
        user_obj = inline_query.from_user
        user_id = user_obj.id
        user_name = f"@{user_obj.username}" if user_obj.username else user_id
        
        # 1. FILTRO DE SEGURIDAD EXCLUSIVO PARA ADMINS
        if user_id not in USUARIOS_AUTORIZADOS and user_name not in USUARIOS_AUTORIZADOS:
            bot.answer_inline_query(inline_query.id, [], cache_time=1)
            return

        texto_busqueda = inline_query.query.strip().lower()
        resultados = []

        # --- OPCIÓN 1: Escribe 'p' o '/p' ---
        if texto_busqueda in ['p', '/p']:
            texto_p = construir_monitor_texto_html()
            resultados.append(
                types.InlineQueryResultArticle(
                    id='p2p_inline',
                    title="📊 Reporte Monitor P2P",
                    description="Publicar tabla P2P con rangos y emojis animados",
                    input_message_content=types.InputTextMessageContent(
                        message_text=texto_p,
                        parse_mode='HTML'
                    )
                )
            )

        # --- OPCIÓN 2: Escribe 'i' o '/i' ---
        elif texto_busqueda in ['i', '/i']:
            texto_i = construir_intervencion_texto_html(user=user_obj)
            resultados.append(
                types.InlineQueryResultArticle(
                    id='intervencion_inline',
                    title="🏦 Reporte Intervención",
                    description="Publicar calculador de intervención en el canal",
                    input_message_content=types.InputTextMessageContent(
                        message_text=texto_i,
                        parse_mode='HTML'
                    )
                )
            )

        # --- OPCIÓN 3: Escribe 'tasas' o '/tasas' ---
        elif texto_busqueda in ['tasas', '/tasas', 'tasa']:
            texto_tasas = construir_monitor_canal_html()
            resultados.append(
                types.InlineQueryResultArticle(
                    id='tasas_inline',
                    title="📈 Resumen Tasas Vivo",
                    description="Publicar ficha corta de Binance P2P",
                    input_message_content=types.InputTextMessageContent(
                        message_text=texto_tasas,
                        parse_mode='HTML'
                    )
                )
            )

        # --- OPCIÓN POR DEFECTO ---
        else:
            texto_p = construir_monitor_texto_html()
            texto_i = construir_intervencion_texto_html(user=user_obj)
            texto_tasas = construir_monitor_canal_html()

            resultados = [
                types.InlineQueryResultArticle(
                    id='p2p_default',
                    title="📊 Monitor P2P Completo",
                    description="Toca para publicar reporte completo P2P",
                    input_message_content=types.InputTextMessageContent(message_text=texto_p, parse_mode='HTML')
                ),
                types.InlineQueryResultArticle(
                    id='tasas_default',
                    title="📈 Ficha Tasas en Vivo",
                    description="Toca para publicar ficha corta Binance",
                    input_message_content=types.InputTextMessageContent(message_text=texto_tasas, parse_mode='HTML')
                ),
                types.InlineQueryResultArticle(
                    id='intervencion_default',
                    title="🏦 Calculadora Intervención",
                    description="Toca para publicar Intervención BCV",
                    input_message_content=types.InputTextMessageContent(message_text=texto_i, parse_mode='HTML')
                )
            ]

        bot.answer_inline_query(inline_query.id, resultados, cache_time=1)

    except Exception as e:
        print(f"Error en inline_query: {e}")
        

# ==========================================
#            EJECUCIÓN DEL BOT
# ==========================================

if __name__ == "__main__":
    # Carga la tasa guardada en disco antes de iniciar
    cargar_cache_de_disco()

    # Limpia webhooks y descarta actualizaciones pendientes
    try:
        bot.remove_webhook(drop_pending_updates=True)
        time.sleep(1)
    except Exception:
        pass

    # 🟢 1. Definimos los canales/grupos donde rotará el anuncio de captcha
    CHATS_ANUNCIOS = [CANAL_PRUEBA, CANAL_CONGESTIONADO]

    # 🟢 2. Activamos el ciclo de anuncios pasando bot y la lista de chats
    iniciar_modulo_anuncios(bot, CHATS_ANUNCIOS)

    print("🚀 Bot Maestro en línea con limpieza automática y temporizador de 5 min...")

    # Inicia el receptor webhook en segundo plano
    threading.Thread(target=iniciar_servidor_receptor, daemon=True).start()

    # Arranca el polling limpio
    bot.infinity_polling()
    

    
