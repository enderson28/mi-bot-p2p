import json
import logging
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from datetime import datetime, time

logger = logging.getLogger(__name__)

USER_ARBITRAJE_DATA = {}

COMISIONES_BANCOS = {
    "provincial": {"nombre": "🏛️ BBVA Provincial (0%)", "comision": 0.00},
    "bdv_debit": {"nombre": "🏛️ BDV Masterdebit (1.5%)", "comision": 0.015},
    "bdv_credit": {"nombre": "🏛️ BDV Credit / Tesoro / Otros (2.5%)", "comision": 0.025},
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


def calcular_arbitraje_reposicion(monto_usd, comision_banco, tasa_bcv_hoy, tasa_bcv_manana, tasa_p2p_venta):
    tasa_interv_hoy = tasa_bcv_hoy * 1.005
    bs_invertidos_hoy = monto_usd * tasa_interv_hoy

    usd_tras_banco = monto_usd * (1 - comision_banco)
    usdt_netos_binance = usd_tras_banco * (1 - COMISION_PASARELA_BINANCE)

    usdt_recuperar_hoy = bs_invertidos_hoy / tasa_p2p_venta
    ganancia_usdt_hoy = usdt_netos_binance - usdt_recuperar_hoy
    ganancia_bs_hoy = ganancia_usdt_hoy * tasa_p2p_venta

    tasa_interv_manana = (tasa_bcv_manana if tasa_bcv_manana else tasa_bcv_hoy) * 1.005
    bs_necesarios_manana = monto_usd * tasa_interv_manana
    usdt_recuperar_manana = bs_necesarios_manana / tasa_p2p_venta
    ganancia_usdt_manana = usdt_netos_binance - usdt_recuperar_manana
    ganancia_bs_manana = ganancia_usdt_manana * tasa_p2p_venta

    return {
        "tasa_interv_hoy": tasa_interv_hoy,
        "bs_invertidos_hoy": bs_invertidos_hoy,
        "usdt_netos_binance": usdt_netos_binance,
        "usdt_recuperar_hoy": usdt_recuperar_hoy,
        "ganancia_usdt_hoy": ganancia_usdt_hoy,
        "ganancia_bs_hoy": ganancia_bs_hoy,
        "tasa_interv_manana": tasa_interv_manana,
        "bs_necesarios_manana": bs_necesarios_manana,
        "usdt_recuperar_manana": usdt_recuperar_manana,
        "ganancia_usdt_manana": ganancia_usdt_manana,
        "ganancia_bs_manana": ganancia_bs_manana,
    }


def registrar_handlers_arbitraje(bot, redis_client):

    # --- HANDLER PARA SALIR AL MENÚ ---
    @bot.callback_query_handler(func=lambda call: call.data == "arb_salir_menu")
    def salir_al_menu(call):
        bot.answer_callback_query(call.id)
        chat_id = call.message.chat.id
        user_id = call.from_user.id

        # Limpiamos hilos de conversación pendientes en el chat
        bot.clear_step_handler_by_chat_id(chat_id)
        if user_id in USER_ARBITRAJE_DATA:
            del USER_ARBITRAJE_DATA[user_id]

        bot.send_message(
            chat_id,
            "⬅️ *Menú restablecido.* Puedes seleccionar cualquier opción del teclado inferior.",
            parse_mode="Markdown"
        )


    # --- INICIO DE ARBITRAJE ---
    @bot.message_handler(func=lambda message: message.text == "📊 Arbitraje & Reposición")
    @bot.callback_query_handler(func=lambda call: call.data == "calc_arbitraje")
    def iniciar_arbitraje(event):
        if hasattr(event, 'data'):
            bot.answer_callback_query(event.id)
            chat_id = event.message.chat.id
            user_id = event.from_user.id
        else:
            chat_id = event.chat.id
            user_id = event.from_user.id

        # Limpiamos handlers previos por seguridad
        bot.clear_step_handler_by_chat_id(chat_id)

        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("🏛️ BBVA Provincial (0%)", callback_data="arb_banco_provincial"),
            InlineKeyboardButton("🏛️ BDV Masterdebit (1.5%)", callback_data="arb_banco_bdv_debit"),
            InlineKeyboardButton("🏛️ BDV Credit / Tesoro / Otros (2.5%)", callback_data="arb_banco_bdv_credit"),
            InlineKeyboardButton("⬅️ Salir al menú", callback_data="arb_salir_menu")
        )

        bot.send_message(
            chat_id,
            "📊 *Calculadora de Arbitraje & Reposición*\n\n"
            "Selecciona el *banco / método de pago* utilizado para la compra en Intervención:",
            parse_mode="Markdown",
            reply_markup=markup
        )


    @bot.callback_query_handler(func=lambda call: call.data.startswith("arb_banco_"))
    def seleccionar_banco(call):
        bot.answer_callback_query(call.id)
        chat_id = call.message.chat.id
        user_id = call.from_user.id
        banco_key = call.data.replace("arb_banco_", "")

        if banco_key not in COMISIONES_BANCOS:
            bot.send_message(chat_id, "❌ Opción no válida.")
            return

        USER_ARBITRAJE_DATA[user_id] = {
            "banco_key": banco_key,
            "comision_banco": COMISIONES_BANCOS[banco_key]["comision"],
            "nombre_banco": COMISIONES_BANCOS[banco_key]["nombre"],
        }

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⬅️ Salir al menú", callback_data="arb_salir_menu"))

        msg = bot.send_message(
            chat_id,
            f"✅ Selección: *{COMISIONES_BANCOS[banco_key]['nombre']}*\n\n"
            "💵 *Escribe el monto en USD* que compraste en el banco:\n"
            "_(Ejemplo: 500 o 300)_",
            parse_mode="Markdown",
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, solicitar_tasa_p2p, bot, redis_client, user_id)


    def solicitar_tasa_p2p(message, bot, redis_client, user_id):
        chat_id = message.chat.id
        text = message.text.strip().replace(",", ".")

        # Si el usuario presiona un botón del teclado principal a mitad del flujo, abortar silenciosamente
        if text in ["🟢 P2P-USDT 🔴", "📊 Intervencion 📊", "📟 Calculadora", "⚙️ Soporte", "🤖 IA Consulta", "📊 Arbitraje & Reposición"]:
            bot.clear_step_handler_by_chat_id(chat_id)
            return

        try:
            monto_usd = float(text)
            if monto_usd <= 0: raise ValueError()
        except ValueError:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("⬅️ Salir al menú", callback_data="arb_salir_menu"))
            
            msg = bot.send_message(
                chat_id, 
                "❌ *Monto inválido.* Ingresa un número en USD (ejemplo: `500`):", 
                parse_mode="Markdown",
                reply_markup=markup
            )
            bot.register_next_step_handler(msg, solicitar_tasa_p2p, bot, redis_client, user_id)
            return

        USER_ARBITRAJE_DATA[user_id]["monto_usd"] = monto_usd

        cache_data = obtener_datos_cache_redis(redis_client)
        tasa_p2p_auto = obtener_tasa_p2p_por_rango(cache_data, monto_usd)
        
        USER_ARBITRAJE_DATA[user_id]["tasa_p2p_auto"] = tasa_p2p_auto
        USER_ARBITRAJE_DATA[user_id]["cache_data"] = cache_data

        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton(f"🔴 Usar Tasa Monitor ({tasa_p2p_auto:.2f} Bs)", callback_data="arb_p2p_auto"),
            InlineKeyboardButton("⬅️ Salir al menú", callback_data="arb_salir_menu")
        )

        msg = bot.send_message(
            chat_id,
            f"🔴 *Tasa de Venta P2P (USDT)*\n\n"
            f"Escribe manualmente la *tasa a la que vas a vender* (Ej: `890` o `892.5`):\n\n"
            f"_O presiona el botón si deseas usar la tasa detectada por el monitor para tu rango:_",
            parse_mode="Markdown",
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, procesar_tasa_p2p_manual, bot, redis_client, user_id)


    @bot.callback_query_handler(func=lambda call: call.data == "arb_p2p_auto")
    def usar_p2p_auto(call):
        bot.answer_callback_query(call.id)
        chat_id = call.message.chat.id
        user_id = call.from_user.id

        bot.clear_step_handler_by_chat_id(chat_id)

        if user_id in USER_ARBITRAJE_DATA:
            tasa_auto = USER_ARBITRAJE_DATA[user_id].get("tasa_p2p_auto", 890.0)
            generar_y_enviar_resultado(chat_id, user_id, tasa_auto, bot, redis_client)


    def procesar_tasa_p2p_manual(message, bot, redis_client, user_id):
        chat_id = message.chat.id
        text = message.text.strip().replace(",", ".")

        # Si presiona una opción del menú de botones flotantes
        if text in ["🟢 P2P-USDT 🔴", "📊 Intervencion 📊", "📟 Calculadora", "⚙️ Soporte", "🤖 IA Consulta", "📊 Arbitraje & Reposición"]:
            bot.clear_step_handler_by_chat_id(chat_id)
            return

        try:
            tasa_p2p = float(text)
            if tasa_p2p <= 0: raise ValueError()
        except ValueError:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("⬅️ Salir al menú", callback_data="arb_salir_menu"))

            msg = bot.send_message(
                chat_id, 
                "❌ *Tasa inválida.* Ingresa un número de tasa válido (ej: `890`):", 
                parse_mode="Markdown",
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

        tasa_bcv_actual = float(cache_data.get("bcv_tasa", 756.71))
        tasa_bcv_anterior = float(cache_data.get("bcv_tasa_anterior", tasa_bcv_actual))

        # --- LÓGICA DE DETECCIÓN DE FECHA Y HORA DE REPOSICIÓN ---
        # Revisamos si la tasa actual cambió respecto a la anterior
        hay_nueva_tasa_publicada = (tasa_bcv_actual != tasa_bcv_anterior) and (tasa_bcv_actual > tasa_bcv_anterior)

        # Si hay nueva tasa publicada (usualmente después de las 4:00 PM - 5:00 PM):
        # La compra del día se hizo a la tasa anterior y la nueva tasa aplica para reposición de mañana.
        if hay_nueva_tasa_publicada:
            tasa_bcv_hoy = tasa_bcv_anterior
            tasa_bcv_manana = tasa_bcv_actual
        else:
            # Durante la mañana / tarde (antes del reporte del BCV):
            # La compra de hoy es con la tasa actual y aún no hay proyección para mañana.
            tasa_bcv_hoy = tasa_bcv_actual
            tasa_bcv_manana = None

        res = calcular_arbitraje_reposicion(
            monto_usd=monto_usd,
            comision_banco=comision_banco,
            tasa_bcv_hoy=tasa_bcv_hoy,
            tasa_bcv_manana=tasa_bcv_manana,
            tasa_p2p_venta=tasa_p2p_venta
        )

        msj = (
            f"📊 *RESULTADO DE ARBITRAJE & REPOSICIÓN*\n\n"
            f"🏛️ *Banco:* {data_user.get('nombre_banco')}\n"
            f"💵 *Monto Comprado:* ${monto_usd:,.2f} USD\n"
            f"🏦 *Tasa Compra (Hoy):* {res['tasa_interv_hoy']:,.2f} Bs/USD\n"
            f"🔴 *Tasa Venta P2P:* {tasa_p2p_venta:,.2f} Bs/USDT\n\n"
            f"📥 *USDT Líquidos Binance:* `{res['usdt_netos_binance']:,.2f} USDT`\n"
            f"💸 *Inversión de Hoy:* `{res['bs_invertidos_hoy']:,.2f} Bs`\n"
            f"───────────────────────────\n"
            f"1️⃣ *RECUPERAR CAPITAL HOY*\n"
            f"• Vender en P2P: `{res['usdt_recuperar_hoy']:,.2f} USDT`\n"
            f"🎉 *Ganancia:* `+{res['ganancia_usdt_hoy']:,.2f} USDT` (~{res['ganancia_bs_hoy']:,.2f} Bs)\n"
        )

        # Solo muestra la sección de "Reposición para Mañana" si el BCV ya publicó el nuevo cambio en la tarde
        if tasa_bcv_manana:
            diferencia_bcv = tasa_bcv_manana - tasa_bcv_hoy
            msj += (
                f"\n2️⃣ *REPOSICIÓN PARA MAÑANA (BCV Actualizado)*\n"
                f"📌 *Nueva Tasa BCV (+0.5%):* {res['tasa_interv_manana']:,.2f} Bs/USD (+{diferencia_bcv:,.2f} Bs)\n"
                f"• Bs necesarios mañana: `{res['bs_necesarios_manana']:,.2f} Bs`\n"
                f"• Vender en P2P: `{res['usdt_recuperar_manana']:,.2f} USDT`\n"
                f"🛡️ *Ganancia Real Aislada:* `+{res['ganancia_usdt_manana']:,.2f} USDT` (~{res['ganancia_bs_manana']:,.2f} Bs)\n"
            )
        else:
            msj += (
                f"\nℹ️ _Tasa BCV de mañana aún no publicada por el BCV. "
                f"Usa este cálculo para tu operación de hoy._\n"
            )

        msj += "───────────────────────────"

        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("🔄 Calcular otro monto", callback_data="calc_arbitraje"),
            InlineKeyboardButton("⬅️ Salir al menú", callback_data="arb_salir_menu")
        )

        bot.send_message(chat_id, msj, parse_mode="Markdown", reply_markup=markup)

        if user_id in USER_ARBITRAJE_DATA:
            del USER_ARBITRAJE_DATA[user_id]





