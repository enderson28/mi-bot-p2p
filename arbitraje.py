import json
import logging
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, time, timedelta, timezone

logger = logging.getLogger(__name__)

USER_ARBITRAJE_DATA = {}

# --- DICCIONARIO DE EMOJIS ANIMADOS (Telegram Premium HTML) ---
# Puedes ajustar los IDs aquí si deseas cambiar alguno en el futuro
TG_EMOJIS = {
    "calc": '<tg-emoji emoji-id="5303214794336125778">🧮</tg-emoji>',
    "usdt1": '<tg-emoji emoji-id="5843796824367832872">🪙</tg-emoji>',
    "check": '<tg-emoji emoji-id="5206607081334906820">✔️</tg-emoji>',
    "pencil": '<tg-emoji emoji-id="5395444784611480792">✏️</tg-emoji>',
    "bank": '<tg-emoji emoji-id="5332455502917949981">🏦</tg-emoji>',
    "dollar": '<tg-emoji emoji-id="5409048419211682843">💵</tg-emoji>',
    "percent": '<tg-emoji emoji-id="5229064374403998351">🛍</tg-emoji>',
    "chart": '<tg-emoji emoji-id="5197503331215361533">📈</tg-emoji>',
    "red_circle": '<tg-emoji emoji-id="5411225014148014586">🔴</tg-emoji>',
    "green_circle": '<tg-emoji emoji-id="5416081784641168838">🟢</tg-emoji>',
    "usdt": '<tg-emoji emoji-id="5814556334829343625">🪙</tg-emoji>',
    "usd": '<tg-emoji emoji-id="5325517150754986636">🪙</tg-emoji>',
    "binance": '<tg-emoji emoji-id="5830062858985018281">🪙</tg-emoji>',
    "hand": '<tg-emoji emoji-id="5264713049637409446">🪙</tg-emoji>',
    "briefcase": '<tg-emoji emoji-id="5445221832074483553">💼</tg-emoji>',
    "party": '<tg-emoji emoji-id="5461151367559141950">🎉</tg-emoji>',
    "bcv": '<tg-emoji emoji-id="5143558232739940356">🪛</tg-emoji>',
    "pro": '<tg-emoji emoji-id="4949492420392781701">🕘</tg-emoji>',
    "bdv1": '<tg-emoji emoji-id="4949813911579788830">🔉</tg-emoji>',
    "bdv2": '<tg-emoji emoji-id="4949567234428110351">🌁</tg-emoji>',
    "teso": '<tg-emoji emoji-id="4949973031528170774">🕥</tg-emoji>',
    "bancaamiga": '<tg-emoji emoji-id="4947747894871460151">😶‍🌫️</tg-emoji>',
    "bancoactivo": '<tg-emoji emoji-id="4949649440102156194">☄️</tg-emoji>',
    "zinli": '<tg-emoji emoji-id="4949657248352700116">😛</tg-emoji>',
    "banesco": '<tg-emoji emoji-id="4949457545258338260">👎</tg-emoji>',
    "mercantil": '<tg-emoji emoji-id="4949779543251486291">😀</tg-emoji>',
    "bfc": '<tg-emoji emoji-id="4949958450114201616">😁</tg-emoji>',
    "bnc": '<tg-emoji emoji-id="5100832907396646323">😃</tg-emoji>',
    "bancoexterior": '<tg-emoji emoji-id="4949665988611146999">😉</tg-emoji>',
    "clic": '<tg-emoji emoji-id="5310278924616356636">🎯</tg-emoji>',
    
}

COMISIONES_BANCOS = {
    "provincial": {
        "emoji": TG_EMOJIS["pro"],
        "nombre": "BBVA Provincial",
        "porcentaje_str": f"1.5{TG_EMOJIS['percent']}",
        "comision": 0.015,
    },
    "bdv_debit": {
        "emoji": TG_EMOJIS["bdv1"],
        "nombre": "BDV Masterdebit",
        "porcentaje_str": f"1.5{TG_EMOJIS['percent']}",
        "comision": 0.015,
    },
    "otros_1_5": {
        "emoji": TG_EMOJIS["clic"],
        "nombre": "Otros Bancos",
        "porcentaje_str": f"1.5{TG_EMOJIS['percent']}",
        "comision": 0.015,
    },
    "bdv_master": {
        "emoji": TG_EMOJIS["bdv2"],
        "nombre": "BDV MASTERCARD",
        "porcentaje_str": f"2.5{TG_EMOJIS['percent']}",
        "comision": 0.025,
    },
    "tesoro": {
        "emoji": TG_EMOJIS["teso"],
        "nombre": "BANCO TESORO",
        "porcentaje_str": f"2.5{TG_EMOJIS['percent']}",
        "comision": 0.025,
    },
    "otros_2_5": {
        "emoji": TG_EMOJIS["clic"],
        "nombre": "otros bancos",
        "porcentaje_str": f"2.5{TG_EMOJIS['percent']}",
        "comision": 0.025,
    },
    "activo": {
        "emoji": TG_EMOJIS["bancoactivo"],
        "nombre": "BANCO ACTIVO",
        "porcentaje_str": f"3{TG_EMOJIS['percent']}",
        "comision": 0.030,
    },    
    "amiga": {
        "emoji": TG_EMOJIS["bancaamiga"],
        "nombre": "BANCO BANCAMIGA",
        "porcentaje_str": f"5{TG_EMOJIS['percent']}",
        "comision": 0.050,
    },
    "mercantil": {
        "emoji": TG_EMOJIS["mercantil"],
        "nombre": "MERCANTIL",
        "porcentaje_str": f"{TG_EMOJIS['zinli']}",
        "comision": 0.0,
    },   
}

COMISION_PASARELA_BINANCE = 0.041  # 4.1% fija


def obtener_datos_cache_redis(redis_client):
    try:
        data_raw = redis_client.get("CACHE_TASAS_STORAGE")
        if data_raw:
            if isinstance(data_raw, bytes):
                data_raw = data_raw.decode('utf-8')
            return json.loads(data_raw) if isinstance(data_raw, str) else data_raw
    except Exception as e:
        logger.error(f"Error al leer CACHE_TASAS_STORAGE de Redis: {e}")
    return None


def obtener_tasa_p2p_por_rango(cache_data, monto_usd):
    if not cache_data or "rangos" not in cache_data:
        return 890.0

    rangos = cache_data.get("rangos", {})

    if monto_usd < 100:
        key_rango = "50.0"
    elif monto_usd < 500:
        key_rango = "150.0"
    else:
        key_rango = "500.0"

    datos_rango = rangos.get(key_rango) or rangos.get(float(key_rango)) or {}
    tasa_venta = datos_rango.get("venta", 0.0)

    return float(tasa_venta) if tasa_venta > 0 else 890.0


def obtener_precio_spot_usdt_usd(cache_data=None):
    if cache_data and "usdt_usd_spot" in cache_data:
        try:
            val = float(cache_data["usdt_usd_spot"])
            if val > 0:
                return 1 / val if val > 1.0 else val
        except (ValueError, TypeError):
            pass

    try:
        url = "https://api.binance.com/api/v3/ticker/price?symbol=USDTUSD"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            precio = float(response.json().get("price", 0.9987))
            return 1 / precio if precio > 1.0 else precio
    except Exception as e:
        logger.warning(f"No se pudo consultar Binance Spot USDTUSD: {e}")

    return 0.9987


def calcular_arbitraje_reposicion(monto_usd, comision_banco, tasa_bcv_hoy, tasa_bcv_manana, tasa_p2p_venta, tasa_usd_usdt=0.9987, tasa_zinli=None):
    tasa_interv_hoy = tasa_bcv_hoy
    bs_invertidos_hoy = monto_usd * tasa_interv_hoy

    usd_tras_banco = monto_usd * (1 - comision_banco)
    usd_fiat_netos = usd_tras_banco * (1 - COMISION_PASARELA_BINANCE)
    
    # Si viene tasa_zinli se calcula la conversión Zinli -> USDT, si no, usa el cálculo de pasarela
    if tasa_zinli and tasa_zinli > 0:
        usdt_brutos = monto_usd / tasa_zinli
        comision_taker = usdt_brutos * 0.00041  # Tarifa Taker de Binance (~0.08 USDT en $200)
        usdt_netos_binance = usdt_brutos - comision_taker
    else:
        comision_taker = 0.0
        usd_tras_banco = monto_usd * (1 - comision_banco)
        usd_fiat_netos = usd_tras_banco * (1 - COMISION_PASARELA_BINANCE)
        usdt_netos_binance = usd_fiat_netos / tasa_usd_usdt if tasa_usd_usdt > 0 else usd_fiat_netos

    usdt_recuperar_hoy = bs_invertidos_hoy / tasa_p2p_venta
    ganancia_usdt_hoy = usdt_netos_binance - usdt_recuperar_hoy
    ganancia_bs_hoy = ganancia_usdt_hoy * tasa_p2p_venta

    tasa_interv_manana = tasa_bcv_manana if tasa_bcv_manana else tasa_bcv_hoy
    bs_necesarios_manana = monto_usd * tasa_interv_manana
    usdt_recuperar_manana = bs_necesarios_manana / tasa_p2p_venta
    ganancia_usdt_manana = usdt_netos_binance - usdt_recuperar_manana
    ganancia_bs_manana = ganancia_usdt_manana * tasa_p2p_venta

    return {
        "tasa_interv_hoy": tasa_interv_hoy,
        "bs_invertidos_hoy": bs_invertidos_hoy,
        "usd_fiat_netos": usd_fiat_netos,
        "usdt_netos_binance": usdt_netos_binance,
        "usdt_recuperar_hoy": usdt_recuperar_hoy,
        "ganancia_usdt_hoy": ganancia_usdt_hoy,
        "ganancia_bs_hoy": ganancia_bs_hoy,
        "tasa_interv_manana": tasa_interv_manana,
        "bs_necesarios_manana": bs_necesarios_manana,
        "usdt_recuperar_manana": usdt_recuperar_manana,
        "ganancia_usdt_manana": ganancia_usdt_manana,
        "ganancia_bs_manana": ganancia_bs_manana,
        "comision_taker": comision_taker,
    }


def registrar_handlers_arbitraje(bot, redis_client):

    # --- HANDLER SALIR AL MENÚ ---
    @bot.callback_query_handler(func=lambda call: call.data == "arb_salir_menu")
    def salir_al_menu(call):
        bot.answer_callback_query(call.id)
        chat_id = call.message.chat.id
        user_id = call.from_user.id

        bot.clear_step_handler_by_chat_id(chat_id)
        if user_id in USER_ARBITRAJE_DATA:
            del USER_ARBITRAJE_DATA[user_id]

        bot.send_message(
            chat_id,
            "🏠 Menú restablecido. Puedes seleccionar cualquier opción del teclado inferior.",
            parse_mode="Markdown"
        )

    # --- PASO 1: SELECCIONAR BANCO ---
    @bot.message_handler(func=lambda message: message.text in ["📊 Arbitraje & Reposición", "Arbitraje & Reposición"])
    @bot.callback_query_handler(func=lambda call: call.data == "calc_arbitraje")
    def iniciar_arbitraje(event):
        if hasattr(event, 'data'):
            bot.answer_callback_query(event.id)
            chat_id = event.message.chat.id
        else:
            chat_id = event.chat.id

        bot.clear_step_handler_by_chat_id(chat_id)

        # Los botones Inline llevan Emojis Unicode estándar (no soportan custom animados)
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("1. 🏦 BBVA PROVINCIAL (1.5%)", callback_data="arb_banco_provincial"),
            InlineKeyboardButton("2. 💳 BDV MASTERDEBIT (1.5%)", callback_data="arb_banco_bdv_debit"),
            InlineKeyboardButton("3. 📲 Otros Bancos (1.5%)", callback_data="arb_banco_otros_1_5"),
            InlineKeyboardButton("4. 💳 BDV MASTERCARD (2.5%)", callback_data="arb_banco_bdv_master"),
            InlineKeyboardButton("5. 🏛️ BANCO TESORO (2.5%)", callback_data="arb_banco_tesoro"),
            InlineKeyboardButton("6. 📲 otros bancos (2.5%)", callback_data="arb_banco_otros_2_5"),
            InlineKeyboardButton("7. 🏦 BANCO ACTIVO (3%)", callback_data="arb_banco_activo"),
            InlineKeyboardButton("8. 🏦 BANCO BANCAMIGA (5%)", callback_data="arb_banco_amiga"),
            InlineKeyboardButton("9. 🏦 MERCANTIL", callback_data="arb_banco_mercantil"),
            InlineKeyboardButton("⬅️ Salir al Menu", callback_data="arb_salir_menu")
        )

        msg_text = (
            f"{TG_EMOJIS['calc']} <b>Calculadora de Arbitraje & Reposición</b>\n\n"
            f"Selecciona el banco {TG_EMOJIS['bank']} / método de pago utilizado para la compra en Intervención:"
        )

        bot.send_message(
            chat_id,
            msg_text,
            parse_mode="HTML",
            reply_markup=markup
        )

    # --- PASO 2: SOLICITAR MONTO EN USD ---
    @bot.callback_query_handler(func=lambda call: call.data.startswith("arb_banco_"))
    def seleccionar_banca(call):
        bot.answer_callback_query(call.id)
        chat_id = call.message.chat.id
        user_id = call.from_user.id
        banco_key = call.data.replace("arb_banco_", "")

        if banco_key not in COMISIONES_BANCOS:
            bot.send_message(chat_id, "❌ Opción no válida.")
            return

        banco_info = COMISIONES_BANCOS[banco_key]
        
        # Armamos la etiqueta visual con emojis animados (Banco + Nombre + Porcentaje Animado)
        nombre_completo_animado = f"{banco_info['emoji']} {banco_info['nombre']} ({banco_info['porcentaje_str']})"

        USER_ARBITRAJE_DATA[user_id] = {
            "banco_key": banco_key,
            "comision_banco": banco_info["comision"],
            "nombre_banco": nombre_completo_animado,
        }

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⬅️ Salir al menú", callback_data="arb_salir_menu"))

        msg_text = (
            f"{TG_EMOJIS['check']} <b>Selección:</b> {nombre_completo_animado}\n\n"
            f"{TG_EMOJIS['pencil']} Escribe el monto en {TG_EMOJIS['dollar']} <b>USD</b> que compraste en el "
            f"{TG_EMOJIS['bank']} Banco: <i>(Ejemplo: 500 o 300)</i>"
        )

        msg = bot.send_message(
            chat_id,
            msg_text,
            parse_mode="HTML",
            reply_markup=markup
        )

        bot.register_next_step_handler(msg, solicitar_tasa_p2p, bot, redis_client, user_id)


    # --- PASO 3: SOLICITAR TASA DE VENTA / MOSTRAR BOTÓN DE MONITOR ---
    def solicitar_tasa_p2p(message, bot, redis_client, user_id):
        chat_id = message.chat.id
        text = message.text.strip().replace(",", ".")

        if text in ["🟢 P2P-USDT 🔴", "📊 Intervencion 📊", "📟 Calculadora", "⚙️ Soporte", "🤖 IA Consulta", "📊 Arbitraje & Reposición"]:
            bot.clear_step_handler_by_chat_id(chat_id)
            return

        try:
            monto_usd = float(text)
            if monto_usd <= 0:
                raise ValueError()
        except ValueError:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("⬅️ Salir al menú", callback_data="arb_salir_menu"))
            msg = bot.send_message(
                chat_id,
                "❌ <b>Monto inválido.</b> Ingresa un número en USD (ejemplo: '500'):",
                parse_mode="HTML",
                reply_markup=markup
            )
            bot.register_next_step_handler(msg, solicitar_tasa_p2p, bot, redis_client, user_id)
            return

        USER_ARBITRAJE_DATA[user_id]["monto_usd"] = monto_usd

        cache_data = obtener_datos_cache_redis(redis_client)
        USER_ARBITRAJE_DATA[user_id]["cache_data"] = cache_data

        banco_key = USER_ARBITRAJE_DATA[user_id].get("banco_key")

        # === DESVÍO ESPECIAL PARA MERCANTIL (ZINLI) ===
        if banco_key == "mercantil":
            # Traemos la tasa de compra USDT desde tu función existente en bot.py
            from bot import obtener_tasa_binance_zinli
            tasa_zinli_auto = obtener_tasa_binance_zinli("buy", monto_usd)
            USER_ARBITRAJE_DATA[user_id]["tasa_zinli_auto"] = tasa_zinli_auto

            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                InlineKeyboardButton(f"🟢 Usar tasa Zinli ({tasa_zinli_auto:.3f} $)", callback_data="arb_zinli_auto"),
                InlineKeyboardButton("⬅️ Salir al menú", callback_data="arb_salir_menu")
            )

            msg_text = (
                f"<blockquote>{TG_EMOJIS['green_circle']} Compra|{TG_EMOJIS['usdt']} en {TG_EMOJIS['zinli']}</blockquote>\n\n"
                f"{TG_EMOJIS['pencil']} Escribe manualmente la tasa a la que compraste en {TG_EMOJIS['zinli']} <i>(Ej: 1.025 o 1.032)</i>:\n"
                f"O presiona {TG_EMOJIS['clic']} el botón si deseas usar la tasa detectada por el monitor:"
            )
            msg = bot.send_message(chat_id, msg_text, parse_mode="HTML", reply_markup=markup)
            bot.register_next_step_handler(msg, procesar_tasa_zinli_manual, bot, redis_client, user_id)
            return

        # === FLUJO NORMAL PARA OTROS BANCOS (VES) ===
        tasa_p2p_auto = obtener_tasa_p2p_por_rango(cache_data, monto_usd)
        USER_ARBITRAJE_DATA[user_id]["tasa_p2p_auto"] = tasa_p2p_auto

        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton(f"🔴 Usar la tasa del monitor ({tasa_p2p_auto:.2f} Bs)", callback_data="arb_p2p_auto"),
            InlineKeyboardButton("⬅️ Salir al menú", callback_data="arb_salir_menu")
        )

        msg_text = (
            f"{TG_EMOJIS['red_circle']} <b>Tasa de Venta P2P {TG_EMOJIS['usdt1']}</b>\n\n"
            f"{TG_EMOJIS['pencil']} Escribe manualmente la tasa a la que vas a vender <i>(Ej: 890 o 892.5)</i>:\n"
            f"O presiona {TG_EMOJIS['clic']} el botón si deseas usar la {TG_EMOJIS['red_circle']} tasa detectada por el monitor:"
        )

        msg = bot.send_message(
            chat_id,
            msg_text,
            parse_mode="HTML",
            reply_markup=markup
        )

        bot.register_next_step_handler(msg, procesar_tasa_p2p_manual, bot, redis_client, user_id)
        
    # --- MANEJADORES EXCLUSIVOS PARA MERCANTIL (ZINLI) ---

    @bot.callback_query_handler(func=lambda call: call.data == "arb_zinli_auto")
    def usar_zinli_auto(call):
        bot.answer_callback_query(call.id)
        chat_id = call.message.chat.id
        user_id = call.from_user.id
        bot.clear_step_handler_by_chat_id(chat_id)

        if user_id in USER_ARBITRAJE_DATA:
            tasa_zinli = USER_ARBITRAJE_DATA[user_id].get("tasa_zinli_auto", 1.025)
            USER_ARBITRAJE_DATA[user_id]["tasa_zinli_usada"] = tasa_zinli
            pedir_tasa_ves_tras_zinli(chat_id, user_id, bot, redis_client)

    def procesar_tasa_zinli_manual(message, bot, redis_client, user_id):
        chat_id = message.chat.id
        text = message.text.strip().replace(",", ".")

        if text in ["🟢 P2P-USDT 🔴", "📊 Intervencion 📊", "📟 Calculadora", "⚙️ Soporte", "🤖 IA Consulta", "📊 Arbitraje & Reposición"]:
            bot.clear_step_handler_by_chat_id(chat_id)
            return

        try:
            tasa_zinli = float(text)
            if tasa_zinli <= 0:
                raise ValueError()
        except ValueError:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("⬅️ Salir al menú", callback_data="arb_salir_menu"))
            msg = bot.send_message(
                chat_id,
                "❌ <b>Tasa Zinli inválida.</b> Ingresa un número válido (ej: 1.028):",
                parse_mode="HTML",
                reply_markup=markup
            )
            bot.register_next_step_handler(msg, procesar_tasa_zinli_manual, bot, redis_client, user_id)
            return

        USER_ARBITRAJE_DATA[user_id]["tasa_zinli_usada"] = tasa_zinli
        pedir_tasa_ves_tras_zinli(chat_id, user_id, bot, redis_client)

    def pedir_tasa_ves_tras_zinli(chat_id, user_id, bot, redis_client):
        monto_usd = USER_ARBITRAJE_DATA[user_id]["monto_usd"]
        cache_data = USER_ARBITRAJE_DATA[user_id]["cache_data"]

        tasa_p2p_auto = obtener_tasa_p2p_por_rango(cache_data, monto_usd)
        USER_ARBITRAJE_DATA[user_id]["tasa_p2p_auto"] = tasa_p2p_auto

        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton(f"🔴 Usar la tasa del monitor ({tasa_p2p_auto:.2f} Bs)", callback_data="arb_p2p_auto"),
            InlineKeyboardButton("⬅️ Salir al menú", callback_data="arb_salir_menu")
        )

        msg_text = (
            f"{TG_EMOJIS['red_circle']} <b>Tasa de Venta P2P {TG_EMOJIS['usdt1']}</b>\n\n"
            f"{TG_EMOJIS['pencil']} Escribe manualmente la tasa a la que vas a vender <i>(Ej: 890 o 892.5)</i>:\n"
            f"O presiona {TG_EMOJIS['clic']} el botón si deseas usar la {TG_EMOJIS['red_circle']} tasa detectada por el monitor:"
        )

        msg = bot.send_message(chat_id, msg_text, parse_mode="HTML", reply_markup=markup)
        bot.register_next_step_handler(msg, procesar_tasa_p2p_manual, bot, redis_client, user_id)
    
    
    # --- HANDLER SI PRESIONA BOTÓN CON TASA DEL MONITOR ---
    @bot.callback_query_handler(func=lambda call: call.data == "arb_p2p_auto")
    def usar_p2p_auto(call):
        bot.answer_callback_query(call.id)
        chat_id = call.message.chat.id
        user_id = call.from_user.id

        bot.clear_step_handler_by_chat_id(chat_id)

        if user_id in USER_ARBITRAJE_DATA:
            tasa_auto = USER_ARBITRAJE_DATA[user_id].get("tasa_p2p_auto", 890.0)
            generar_y_enviar_resultado(chat_id, user_id, tasa_auto, bot, redis_client)

    # --- HANDLER SI ESCRIBE LA TASA MANUALLMENTE ---
    def procesar_tasa_p2p_manual(message, bot, redis_client, user_id):
        chat_id = message.chat.id
        text = message.text.strip().replace(",", ".")

        if text in ["🟢 P2P-USDT 🔴", "📊 Intervencion 📊", "📟 Calculadora", "⚙️ Soporte", "🤖 IA Consulta", "📊 Arbitraje & Reposición"]:
            bot.clear_step_handler_by_chat_id(chat_id)
            return

        try:
            tasa_p2p = float(text)
            if tasa_p2p <= 0:
                raise ValueError()
        except ValueError:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("⬅️ Salir al menú", callback_data="arb_salir_menu"))
            msg = bot.send_message(
                chat_id,
                "❌ <b>Tasa inválida.</b> Ingresa un número de tasa válido (ej: '890'):",
                parse_mode="HTML",
                reply_markup=markup
            )
            bot.register_next_step_handler(msg, procesar_tasa_p2p_manual, bot, redis_client, user_id)
            return

        generar_y_enviar_resultado(chat_id, user_id, tasa_p2p, bot, redis_client)

def generar_y_enviar_resultado(chat_id, user_id, tasa_p2p_venta, bot, redis_client):
    data_user = USER_ARBITRAJE_DATA.get(user_id, {})
    monto_usd = data_user.get("monto_usd", 0)
    comision_banco = data_user.get("comision_banco", 0)
    cache_data = data_user.get("cache_data") or obtener_datos_cache_redis(redis_client) or {}
    
    # 1. Obtener Spot con relación correcta USDT/USD (< 1.0)
    tasa_usd_usdt_raw = obtener_precio_spot_usdt_usd(cache_data)
    tasa_usd_usdt = 1 / tasa_usd_usdt_raw if tasa_usd_usdt_raw > 1.0 else tasa_usd_usdt_raw

    # 2. Extraer tasa Zinli si el banco es Mercantil
    tasa_zinli_usada = data_user.get("tasa_zinli_usada", None)

    # 3. Lógica de Tasas BCV SIN BORRAR la tasa de Mañana
    val_bcv = cache_data.get("bcv_tasa")
    val_manana = cache_data.get("bcv_tasa_manana")

    tasa_bcv_hoy = float(val_bcv or 0.0)
    tasa_bcv_manana = float(val_manana) if (val_manana and float(val_manana) > 0) else None

    # 4. Llamada al cálculo pasando la variable tasa_zinli explícitamente
    res = calcular_arbitraje_reposicion(
        monto_usd=monto_usd,
        comision_banco=comision_banco,
        tasa_bcv_hoy=tasa_bcv_hoy,
        tasa_bcv_manana=tasa_bcv_manana,
        tasa_p2p_venta=tasa_p2p_venta,
        tasa_usd_usdt=tasa_usd_usdt,
        tasa_zinli=tasa_zinli_usada # <--- ¡AHORA SÍ SE ENVÍA A LA FUNCIÓN!
    )
    
    
    # --- BLOQUE 1: RESULTADO PRINCIPAL HOY ---
    msj = (
        f"<blockquote>{TG_EMOJIS['chart']} <b>RESULTADO DE ARBITRAJE & {TG_EMOJIS['clic']} REPOSICIÓN</b></blockquote>\n"
        f"<b>Banco:</b> {data_user.get('nombre_banco', 'Banco')}\n"
        f"{TG_EMOJIS['dollar']} <b>Monto Comprado:</b> ${monto_usd:,.2f} USD\n"
        f"{TG_EMOJIS['bcv']} <b>Tasa Compra (0.5%):</b> {res['tasa_interv_hoy']:,.3f} Bs\n"
    )
    
    # Si usó Zinli, mostramos la línea adicional de Compra Zinli aquí arriba
    if tasa_zinli_usada:
        usdt_bruto_calc = monto_usd / tasa_zinli_usada
        comision_extra = usdt_bruto_calc - res['usdt_netos_binance']
        
        msj += f"{TG_EMOJIS['green_circle']} <b>Compra Zinli:</b> {tasa_zinli_usada:,.3f} $\n"
        msj += f"<blockquote>{TG_EMOJIS['usdt']} <b>USDT Brutos:</b> {usdt_bruto_calc:.2f} ₮</blockquote>\n"
        msj += f"{TG_EMOJIS['calc']} <b>Comisión Binance P2P:</b> -{comision_extra:.2f} ₮\n"
        
    msj += (
        f"{TG_EMOJIS['red_circle']} <b>Tasa Venta P2P:</b> {tasa_p2p_venta:,.2f} Bs/{TG_EMOJIS['usdt']}\n"
        f"<blockquote>{TG_EMOJIS['usdt']} <b>USDT Líquidos {TG_EMOJIS['binance']} Binance:</b> <code>{res['usdt_netos_binance']:,.2f}</code> {TG_EMOJIS['usdt']} ({TG_EMOJIS['usd']}/{TG_EMOJIS['usdt']} {tasa_usd_usdt:.5f})</blockquote>\n"
        f"<blockquote>{TG_EMOJIS['hand']} <b>Inversión de Hoy:</b> <code>{res['bs_invertidos_hoy']:,.0f}</code> Bs</blockquote>\n"
        f"---------------------\n"
        f"{TG_EMOJIS['briefcase']} <b>RECUPERAR CAPITAL HOY</b>\n"
        f"{TG_EMOJIS['binance']} <b>Vender en P2P:</b> <code>{res['usdt_recuperar_hoy']:,.2f}</code> {TG_EMOJIS['usdt']}\n"
        f"<blockquote>{TG_EMOJIS['party']} <b>Ganancia Actual:</b> +<code>{res['ganancia_usdt_hoy']:,.2f}</code> {TG_EMOJIS['usdt']} (<code>{res['ganancia_bs_hoy']:,.2f}</code> Bs)</blockquote>\n"
    )

    # Extraemos el nombre del día directamente de la fecha de mañana en el cache
    fecha_m = cache_data.get("bcv_fecha_manana", "")
    if fecha_m and "," in fecha_m:
        proximo_dia = fecha_m.split(",")[0].strip()
    else:
        # Fallback usando hora Venezuela (-4) para evitar brincos por UTC
        dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        hora_ve = datetime.now(timezone.utc) - timedelta(hours=4)
        proximo_dia = dias_semana[(hora_ve.weekday() + 1) % 7]

    # --- BLOQUE 2: REPOSICIÓN SI YA SALIÓ TASA DE MAÑANA ---
    if tasa_bcv_manana is not None and tasa_bcv_manana > 0:
        diferencia_bcv = tasa_bcv_manana - tasa_bcv_hoy
        msj += (
            f"---------------------\n"
            f"<blockquote>{TG_EMOJIS['clic']} <b>REPOSICIÓN PARA EL {proximo_dia.upper()}</b> (BCV Actualizado)</blockquote>\n"
            f"{TG_EMOJIS['bcv']} <b>Tasa BCV (+0.5%):</b> {res['tasa_interv_manana']:,.3f} Bs (+{diferencia_bcv:,.2f} Bs)\n"
            f"<blockquote>{TG_EMOJIS['bcv']} <b>Bs necesarios:</b> {res['bs_necesarios_manana']:,.0f} Bs</blockquote>\n"
            f"{TG_EMOJIS['binance']} <b>Vender en P2P:</b> <code>{res['usdt_recuperar_manana']:,.2f}</code> {TG_EMOJIS['usdt']}\n"
            f"<blockquote>{TG_EMOJIS['party']} <b>Ganancia Real Aislada:</b> +<code>{res['ganancia_usdt_manana']:,.2f}</code> {TG_EMOJIS['usdt']}</blockquote>\n"
        )
    else:
        msj += (
            f"---------------------\n"
            f"<i>Tasa {TG_EMOJIS['bcv']} del {proximo_dia} aún no publicada {TG_EMOJIS['chart']} por el {TG_EMOJIS['bcv']}</i>\n"
            f"<i>Usa este cálculo {TG_EMOJIS['calc']} para tu operación de hoy.</i>\n"
        )

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🔄 Calcular otro monto", callback_data="calc_arbitraje"),
        InlineKeyboardButton("🔙 Salir al menú", callback_data="arb_salir_menu")
    )

    bot.send_message(chat_id, msj, parse_mode="HTML", reply_markup=markup)

    if user_id in USER_ARBITRAJE_DATA:
        del USER_ARBITRAJE_DATA[user_id]
        
