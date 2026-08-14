import json
import logging
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

# Diccionario temporal en memoria para guardar el estado del flujo por usuario
USER_ARBITRAJE_DATA = {}

# Comisiones por Banco / Tarjeta
COMISIONES_BANCOS = {
    "provincial": {"nombre": "🏛️ BBVA Provincial", "comision": 0.00},
    "bdv_debit": {"nombre": "🏛️ BDV (Masterdebit 1.5%)", "comision": 0.015},
    "bdv_credit": {"nombre": "🏛️ BDV / Tesoro / Otros (2.5%)", "comision": 0.025},
}

COMISION_PASARELA_BINANCE = 0.041  # 4.1% fija


def obtener_tasas_redis(redis_client):
    """
    Obtiene las tasas BCV (hoy y mañana si existe) de la memoria Redis.
    Ajusta las claves 'bcv:tasa_actual' y 'bcv:tasa_manana' según las guarde tu ejecutor.
    """
    try:
        tasa_hoy_raw = redis_client.get("bcv:tasa_actual") or redis_client.get("tasa_bcv")
        tasa_manana_raw = redis_client.get("bcv:tasa_manana")

        tasa_hoy = float(tasa_hoy_raw) if tasa_hoy_raw else None
        tasa_manana = float(tasa_manana_raw) if tasa_manana_raw else None

        return tasa_hoy, tasa_manana
    except Exception as e:
        logger.error(f"Error al obtener tasas BCV de Redis: {e}")
        return None, None


def obtener_tasa_p2p_redis(redis_client, monto_bs):
    """
    Obtiene la tasa de VENTA 🔴 P2P de Redis para el rango de Bs especificado.
    Si no existe por rango, busca una clave fallback de p2p_venta.
    """
    try:
        # Intenta obtener data del monitor P2P guardada en Redis
        p2p_data_raw = redis_client.get("binance:p2p_venta")
        if p2p_data_raw:
            p2p_data = json.loads(p2p_data_raw)
            # Si tienes filtrado por rangos en JSON:
            # Revisa la estructura que usa tu bot actualmente y extrae el valor correspondiente
            if isinstance(p2p_data, dict) and "tasa" in p2p_data:
                return float(p2p_data["tasa"])
            elif isinstance(p2p_data, (int, float)):
                return float(p2p_data)

        # Fallback a un valor numérico si tu Redis guarda la tasa directa
        tasa_directa = redis_client.get("tasa_p2p_venta")
        if tasa_directa:
            return float(tasa_directa)

    except Exception as e:
        logger.error(f"Error al obtener tasa P2P de Redis: {e}")

    return None


def calcular_arbitraje_reposicion(monto_usd, comision_banco, tasa_bcv_hoy, tasa_bcv_manana, tasa_p2p_venta):
    """
    Realiza los cálculos matemáticos completos de arbitraje + reposición por devaluación.
    """
    # 1. Tasa Intervención (+0.5%)
    tasa_interv_hoy = tasa_bcv_hoy * 1.005
    bs_invertidos_hoy = monto_usd * tasa_interv_hoy

    # 2. Descuento de Comisiones hacia Binance
    usd_tras_banco = monto_usd * (1 - comision_banco)
    usdt_netos_binance = usd_tras_banco * (1 - COMISION_PASARELA_BINANCE)

    # 3. Escenario A: Recuperar Capital Exacto gastado hoy
    usdt_recuperar_hoy = bs_invertidos_hoy / tasa_p2p_venta
    ganancia_usdt_hoy = usdt_netos_binance - usdt_recuperar_hoy
    ganancia_bs_hoy = ganancia_usdt_hoy * tasa_p2p_venta

    # 4. Escenario B: Reposición para el día siguiente (si el BCV subió/cambió)
    tasa_interv_manana = (tasa_bcv_manana if tasa_bcv_manana else tasa_bcv_hoy) * 1.005
    bs_necesarios_manana = monto_usd * tasa_interv_manana
    usdt_recuperar_manana = bs_necesarios_manana / tasa_p2p_venta
    ganancia_usdt_manana = usdt_netos_binance - usdt_recuperar_manana
    ganancia_bs_manana = ganancia_usdt_manana * tasa_p2p_venta

    return {
        "monto_usd": monto_usd,
        "tasa_interv_hoy": tasa_interv_hoy,
        "bs_invertidos_hoy": bs_invertidos_hoy,
        "usdt_netos_binance": usdt_netos_binance,
        "usdt_recuperar_hoy": usdt_recuperar_hoy,
        "ganancia_usdt_hoy": ganancia_usdt_hoy,
        "ganancia_bs_hoy": ganancia_bs_hoy,
        "tasa_bcv_manana": tasa_bcv_manana,
        "tasa_interv_manana": tasa_interv_manana,
        "bs_necesarios_manana": bs_necesarios_manana,
        "usdt_recuperar_manana": usdt_recuperar_manana,
        "ganancia_usdt_manana": ganancia_usdt_manana,
        "ganancia_bs_manana": ganancia_bs_manana,
    }


def registrar_handlers_arbitraje(bot, redis_client):
    """
    Registra los comandos, botones inline y filtros de mensajes para la calculadora de arbitraje.
    """

    @bot.callback_query_handler(func=lambda call: call.data == "calc_arbitraje")
    def iniciar_arbitraje(call):
        bot.answer_callback_query(call.id)
        chat_id = call.message.chat.id

        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("🏛️ BBVA Provincial (0%)", callback_data="arb_banco_provincial"),
            InlineKeyboardButton("🏛️ BDV Masterdebit (1.5%)", callback_data="arb_banco_bdv_debit"),
            InlineKeyboardButton("🏛️ BDV Credit / Tesoro / Otros (2.5%)", callback_data="arb_banco_bdv_credit"),
        )

        bot.send_message(
            chat_id,
            "📊 *Calculadora de Arbitraje & Reposición*\n\n"
            "Selecciona el *banco / método de pago* utilizado para la compra de divisas en Intervención:",
            parse_mode="Markdown",
            reply_markup=markup,
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
            "esperando_monto": True,
        }

        msg = bot.send_message(
            chat_id,
            f"✅ Selección: *{COMISIONES_BANCOS[banco_key]['nombre']}*\n\n"
            "💵 *Escribe el monto en USD* que compraste en el banco:\n"
            "_(Ejemplo: 500 o 300)_",
            parse_mode="Markdown",
        )

        # Registrar el siguiente paso para leer el texto ingresado por el usuario
        bot.register_next_step_handler(msg, procesar_monto_usd, bot, redis_client, user_id)


def procesar_monto_usd(message, bot, redis_client, user_id):
    chat_id = message.chat.id

    if user_id not in USER_ARBITRAJE_DATA or not USER_ARBITRAJE_DATA[user_id].get("esperando_monto"):
        return

    text = message.text.strip().replace(",", ".")

    try:
        monto_usd = float(text)
        if monto_usd <= 0:
            raise ValueError()
    except ValueError:
        msg = bot.send_message(chat_id, "❌ *Monto inválido.* Ingresa un número válido en USD (ejemplo: `500`):", parse_mode="Markdown")
        bot.register_next_step_handler(msg, procesar_monto_usd, bot, redis_client, user_id)
        return

    data_user = USER_ARBITRAJE_DATA[user_id]
    data_user["esperando_monto"] = False

    # 1. Obtener Tasas BCV desde Redis
    tasa_bcv_hoy, tasa_bcv_manana = obtener_tasas_redis(redis_client)

    if not tasa_bcv_hoy:
        bot.send_message(chat_id, "⚠️ *Error:* No se pudo obtener la tasa BCV actual desde Redis.", parse_mode="Markdown")
        return

    # 2. Calcular Bolívares necesarios para buscar el rango en P2P
    tasa_interv_temp = tasa_bcv_hoy * 1.005
    bs_est_invertidos = monto_usd * tasa_interv_temp

    # 3. Obtener Tasa P2P Venta 🔴 desde Redis según el rango
    tasa_p2p_venta = obtener_tasa_p2p_redis(redis_client, bs_est_invertidos)

    if not tasa_p2p_venta:
        # Tasa fallback en caso de que no haya data en Redis
        tasa_p2p_venta = 890.00

    # 4. Generar Cálculos
    res = calcular_arbitraje_reposicion(
        monto_usd=monto_usd,
        comision_banco=data_user["comision_banco"],
        tasa_bcv_hoy=tasa_bcv_hoy,
        tasa_bcv_manana=tasa_bcv_manana,
        tasa_p2p_venta=tasa_p2p_venta,
    )

    # 5. Formatear Mensaje de Salida
    msj = (
        f"📊 *RESULTADO DE ARBITRAJE & REPOSICIÓN*\n\n"
        f"🏛️ *Banco:* {data_user['nombre_banco']}\n"
        f"💵 *Monto Comprado:* ${monto_usd:,.2f} USD\n"
        f"🏦 *Tasa BCV + 0.5% (Hoy):* {res['tasa_interv_hoy']:,.2f} Bs/USD\n"
        f"🔴 *Tasa Venta P2P:* {tasa_p2p_venta:,.2f} Bs/USDT\n\n"
        f"📥 *USDT Líquidos en Binance:* `{res['usdt_netos_binance']:,.2f} USDT`\n"
        f"💸 *Total Invertido Hoy:* `{res['bs_invertidos_hoy']:,.2f} Bs`\n"
        f"───────────────────────────\n"
        f"1️⃣ *RECUPERAR CAPITAL HOY*\n"
        f"• Vender en P2P: `{res['usdt_recuperar_hoy']:,.2f} USDT`\n"
        f"🎉 *Ganancia Net:* `+{res['ganancia_usdt_hoy']:,.2f} USDT` (~{res['ganancia_bs_hoy']:,.2f} Bs)\n"
    )

    if tasa_bcv_manana and tasa_bcv_manana != tasa_bcv_hoy:
        diferencia_bcv = tasa_bcv_manana - tasa_bcv_hoy
        msj += (
            f"\n2️⃣ *REPOSICIÓN PARA MAÑANA (BCV Actualizado)*\n"
            f"📌 *Nueva Tasa BCV Mañana:* {tasa_bcv_manana:,.2f} Bs (+{diferencia_bcv:,.2f} Bs)\n"
            f"• Bs necesarios mañana: `{res['bs_necesarios_manana']:,.2f} Bs`\n"
            f"• Vender en P2P: `{res['usdt_recuperar_manana']:,.2f} USDT`\n"
            f"🛡️ *Ganancia Real Aislada:* `+{res['ganancia_usdt_manana']:,.2f} USDT` (~{res['ganancia_bs_manana']:,.2f} Bs)\n"
        )
    else:
        msj += "\n💡 _Aún no hay actualización del BCV para mañana en Redis. La ganancia mostrada mantiene el capital de hoy._\n"

    msj += "───────────────────────────"

    bot.send_message(chat_id, msj, parse_mode="Markdown")

    # Limpiar estado del usuario
    if user_id in USER_ARBITRAJE_DATA:
        del USER_ARBITRAJE_DATA[user_id]
