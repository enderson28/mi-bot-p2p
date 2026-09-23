import json
import logging
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from emojis import TG_EMOJIS, e
from seguridad import es_usuario_vip_activo, responder_sin_acceso_vip

logger = logging.getLogger(__name__)

# Diccionario temporal para almacenar estados de calculadora por usuario
USER_CALC_DATA = {}

def registrar_calculadora(bot, obtener_cache_func, obtener_teclado_func, r=None):
    """
    Registra el módulo de calculadora interactiva de divisas (USD -> Bs, Bs -> USD y USDT -> Bs = USD).
    """

    def obtener_teclado_calc():
        """Devuelve el teclado fijo inferior para la calculadora (4 botones)."""
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row(
            KeyboardButton(f"{TG_EMOJIS['dollar']} USD a 🇻🇪 Bs"),
            KeyboardButton(f"🇻🇪 Bs a {TG_EMOJIS['dollar']} USD")
        )
        markup.row(
            KeyboardButton(f"{TG_EMOJIS['dollar']} USDT a Bs = USD")
        )
        markup.row(
            KeyboardButton(f"{TG_EMOJIS['back']} Volver al menú")
        )
        return markup

    def obtener_tasa_p2p_por_monto(redis_client, key_redis, monto_usdt):
        """Obtiene la tasa de venta P2P (general o BDV) desde Redis según el monto introducido."""
        try:
            if redis_client:
                raw = redis_client.get(key_redis)
                if raw:
                    rangos = json.loads(raw if isinstance(raw, str) else raw.decode('utf-8'))
                    if monto_usdt <= 100:
                        key_rango = "50.0"
                    elif monto_usdt <= 300:
                        key_rango = "150.0"
                    else:
                        key_rango = "300.0"

                    datos_rango = rangos.get(key_rango, {})
                    tasa_venta = datos_rango.get("venta", 0.0)
                    if float(tasa_venta) > 0:
                        return float(tasa_venta)
        except Exception as err:
            logger.error(f"⚠️ Error leyendo {key_redis} en calculadora.py: {err}")
        return 0.0

    @bot.message_handler(func=lambda message: "Calculadora" in message.text if message.text else False)
    def solicitar_monto_mensaje(message, modo="USD_BS"):
        if message.chat.type != "private":
            return

        # CONTROL DE ACCESO VIP
        if not es_usuario_vip_activo(bot, message.from_user, r):
            responder_sin_acceso_vip(bot, message.chat.id)
            return

        bot.clear_step_handler_by_chat_id(message.chat.id)

        if modo == "USD_BS":
            texto_indicacion = (
                f"{e('CALCULADORA', '💬')} <b>CALCULADORA AUTOMÁTICA ({e('BCV', '🏛️')}) (+0.5%)</b>\n\n"
                f"{e('check', '✅')} <b>Modo actual:</b> {e('DINERO', '☺️')} {e('FLECHA_DERECHA', '💬')} 🇻🇪 Bolívares\n"
                f"{e('pencil', '☺️')} Escriba la cifra en (USD) directamente (Ejemplo: 5, 12.5, 100):\n\n"
                f"{e('ARENITA', '⏳')} _Esperando tu monto..._"
            )
        elif modo == "BS_USD":
            texto_indicacion = (
                f"{e('CALCULADORA', '💬')} <b>CALCULADORA DIVISAS AL ({e('BCV', '🏛️')})</b>\n\n"
                f"{e('check', '✅')} <b>Modo actual:</b> 🇻🇪 Bolívares {e('FLECHA_DERECHA', '💬')} {e('DINERO', '💬')}\n"
                f"{e('pencil', '☺️')} Escriba la cifra en (Bs) directamente (Ejemplo: 500, 1500.50):\n\n"
                f"{e('ARENITA', '⏳')} _Esperando tu monto..._"
            )
        else:  # Modo USDT_BS_USD
            texto_indicacion = (
                f"{e('CALCULADORA', '💬')} <b>CALCULADORA {e('USDT', '💬')}USDT a BS = USD</b>\n\n"
                f"{e('check', '✅')} <b>Modo actual:</b> {e('USDT', '💬')} {e('FLECHA_DERECHA', '💬')} Bolívares = USD ({e('BCV', '🏛️')})\n"
                f"{e('pencil', '☺️')} Escribe el monto en (USDT) directamente (Ejemplo: 5, 12.5, 100, 500):\n\n"
                f"{e('ARENITA', '⏳')} _Esperando tu monto..._"
            )

        msg = bot.send_message(
            message.chat.id,
            texto_indicacion,
            parse_mode="HTML",
            reply_markup=obtener_teclado_calc()
        )

        bot.register_next_step_handler(msg, lambda m: procesar_calculo(m, modo))

    def procesar_calculo(message, modo="USD_BS"):
        if message.chat.type != "private":
            return

        texto = message.text.strip() if message.text else ""
        user_id = message.from_user.id

        # 1. Opción de salida al menú principal
        if texto == f"{TG_EMOJIS['back']} Volver al menú" or texto.startswith("/"):
            bot.clear_step_handler_by_chat_id(message.chat.id)
            teclado_restablecido = obtener_teclado_func(message.from_user)
            bot.send_message(
                message.chat.id,
                "📍 Menú principal restablecido.",
                parse_mode="Markdown",
                reply_markup=teclado_restablecido
            )
            return

        # 2. Cambio de modo detectando la intención exacta
        if "USD a" in texto or texto.startswith("💵 USD"):
            solicitar_monto_mensaje(message, modo="USD_BS")
            return
        elif "Bs a" in texto or texto.startswith("🇻🇪 Bs"):
            solicitar_monto_mensaje(message, modo="BS_USD")
            return
        elif "USDT a Bs" in texto:
            solicitar_monto_mensaje(message, modo="USDT_BS_USD")
            return

        # 3. Normalizar comas a puntos
        texto_limpio = texto.replace(",", ".")

        try:
            monto_entrada = float(texto_limpio)
            if monto_entrada <= 0:
                raise ValueError("Monto positivo requerido")
        except ValueError:
            msg_err = bot.send_message(
                message.chat.id,
                "⚠️ <b>Monto inválido.</b> Por favor escribe solo números (Ejemplo: 15 o 20.5) o toca un botón de modo abajo.",
                parse_mode="HTML",
                reply_markup=obtener_teclado_calc()
            )
            bot.register_next_step_handler(msg_err, lambda m: procesar_calculo(m, modo))
            return

        # 4. Obtener datos de tasa BCV desde Redis / Bot
        datos_bcv = obtener_cache_func()
        if isinstance(datos_bcv, dict):
            tasa_hoy = datos_bcv.get("tasa_hoy", 0.0)
            tasa_manana = datos_bcv.get("tasa_manana", 0.0)

            if tasa_manana > 0 and tasa_manana != tasa_hoy:
                tasa_bcv = tasa_manana
                fecha_valor_bcv = datos_bcv.get("fecha_manana", "Mañana")
            else:
                tasa_bcv = tasa_hoy
                fecha_valor_bcv = datos_bcv.get("fecha_hoy", "Hoy")
        else:
            tasa_bcv = float(datos_bcv) if datos_bcv else 0.0
            fecha_valor_bcv = "Hoy"

        tasa_con_intervencion = tasa_bcv * 1.005

        # 5. Cálculos según el modo seleccionado
        if modo == "USD_BS":
            monto_usd = monto_entrada
            monto_bolivares = monto_usd * tasa_con_intervencion

            respuesta = (
                f"{e('CONSULTA1', '💬')} RESULTADO DE CÁLCULO AL ({e('BCV', '🏛️')})\n"
                f"Monto en {e('DINERO', '😁')}: <code>{monto_usd:,.2f}</code> USD\n"
                f"{e('BCV', '🏛️')} Tasa BCV Oficial: {tasa_bcv:,.2f} Bs/$\n"
                f"{e('BALANZA', '⚖️')} Tasa + 0.5%: <code>{tasa_con_intervencion:,.3f}</code> Bs\n"
                f"{e('pago_movil', '💬')} Total a pagar en Bolívares:\n"
                f"{e('FLECHA_DERECHA', '💬')} <b><code>{monto_bolivares:,.2f}</code> Bs</b> ({e('CALENDARIO', '📅')} {fecha_valor_bcv})\n\n"
                f"{e('CHINCHE', '📌')} Puedes seguir escribiendo montos o cambiar de modo abajo."
            )

            msg_res = bot.send_message(
                message.chat.id,
                respuesta,
                parse_mode="HTML",
                reply_markup=obtener_teclado_calc()
            )
            bot.register_next_step_handler(msg_res, lambda m: procesar_calculo(m, modo))

        elif modo == "BS_USD":
            monto_bolivares = monto_entrada
            monto_usd = monto_bolivares / tasa_con_intervencion if tasa_con_intervencion > 0 else 0.0

            respuesta = (
                f"{e('CONSULTA1', '💬')} RESULTADO DE CÁLCULO DIVISAS AL ({e('BCV', '🏛️')})\n"
                f"{e('BOLIVAR', '🚫')} Monto disponible en Bs: <code>{monto_bolivares:,.2f}</code> Bs\n"
                f"{e('BCV', '🏛️')} Tasa BCV Oficial: {tasa_bcv:,.2f} Bs/$\n"
                f"{e('BALANZA', '⚖️')} Tasa + 0.5%: <code>{tasa_con_intervencion:,.3f}</code> Bs\n\n"
                f"Puedes comprar un total de:\n"
                f"{e('FLECHA_DERECHA', '💬')} <b><code>{monto_usd:,.2f}</code> {e('DINERO', '💬')}</b> ({e('CALENDARIO', '📅')} {fecha_valor_bcv})\n\n"
                f"📌 Puedes seguir escribiendo montos o cambiar de modo abajo."
            )

            msg_res = bot.send_message(
                message.chat.id,
                respuesta,
                parse_mode="HTML",
                reply_markup=obtener_teclado_calc()
            )
            bot.register_next_step_handler(msg_res, lambda m: procesar_calculo(m, modo))

        elif modo == "USDT_BS_USD":
            # Guardamos el monto en USDT y los datos BCV para usarlos en la selección de tasa P2P
            USER_CALC_DATA[user_id] = {
                "monto_usdt": monto_entrada,
                "tasa_bcv": tasa_bcv,
                "tasa_con_intervencion": tasa_con_intervencion,
                "fecha_valor_bcv": fecha_valor_bcv
            }

            tasa_p2p_gen = obtener_tasa_p2p_por_monto(r, "p2p_rangos", monto_entrada)
            tasa_p2p_bdv = obtener_tasa_p2p_por_monto(r, "p2p_rangos_bdv", monto_entrada)

            USER_CALC_DATA[user_id]["tasa_p2p_gen"] = tasa_p2p_gen
            USER_CALC_DATA[user_id]["tasa_p2p_bdv"] = tasa_p2p_bdv

            markup_inline = InlineKeyboardMarkup(row_width=1)
            if tasa_p2p_bdv > 0:
                markup_inline.add(
                    InlineKeyboardButton(
                        f"🔴 Usar Venta BDV ({tasa_p2p_bdv:,.2f} Bs)",
                        callback_data="calc_usdt_p2p_bdv"
                    )
                )
            if tasa_p2p_gen > 0:
                markup_inline.add(
                    InlineKeyboardButton(
                        f"🔴 Usar Venta Monitor Pago: Todos ({tasa_p2p_gen:,.2f} Bs)",
                        callback_data="calc_usdt_p2p_gen"
                    )
                )

            txt_pregunta = (
                f"{TG_EMOJIS['dollar']} <b>Monto ingresado:</b> <code>{monto_entrada:,.2f}</code> USDT\n\n"
                f"Selecciona la tasa de venta del monitor P2P que deseas aplicar:"
            )

            msg_res = bot.send_message(
                message.chat.id,
                txt_pregunta,
                parse_mode="HTML",
                reply_markup=markup_inline
            )
            bot.register_next_step_handler(msg_res, lambda m: procesar_calculo(m, modo))

    # --- HANDLERS PARA BOTONES INLINE DE SELECCIÓN DE TASA P2P ---

    def ejecutar_resultado_usdt_bs_usd(call, tasa_p2p, nombre_origen):
        user_id = call.from_user.id
        data = USER_CALC_DATA.get(user_id, {})

        if not data:
            bot.answer_callback_query(call.id, text="❌ Sesión expirada. Ingresa el monto nuevamente.")
            return

        monto_usdt = data.get("monto_usdt", 0.0)
        tasa_bcv = data.get("tasa_bcv", 0.0)
        tasa_con_intervencion = data.get("tasa_con_intervencion", 0.0)
        fecha_valor_bcv = data.get("fecha_valor_bcv", "Hoy")

        if tasa_p2p <= 0 or tasa_bcv <= 0:
            bot.answer_callback_query(call.id, text="❌ Tasa no disponible para realizar el cálculo.")
            return

        total_bs = monto_usdt * tasa_p2p
        usd_bcv_oficial = total_bs / tasa_bcv
        usd_bcv_intervencion = total_bs / tasa_con_intervencion

        respuesta = (
            f"{e('CONSULTA1', '💬')} <b>RESULTADO {e('USDT', '💬')} {e('FLECHA_DERECHA', '💬')} BS = USD</b>\n\n"
            f"<b>{monto_usdt:,.2f} {e('USDT', '💬')}</b>\n"
            f"🇻🇪 <b>Bs al {e('USDT', '💬')} USDT {e('ROJO', '🫠')} Venta {nombre_origen}:</b> <code>{total_bs:,.2f}</code> Bs\n"
            f"   <i>(Tasa aplicada: {tasa_p2p:,.2f} Bs/USDT)</i>\n\n"
            f"{e('BCV', '🏛️')} <b>USD al BCV Oficial:</b> <code>{usd_bcv_oficial:,.2f}</code> $\n"
            f"   <i>(Tasa Oficial: {tasa_bcv:,.2f} Bs/$)</i>\n\n"
            f"{e('BALANZA', '⚖️')} <b>USD al BCV + 0.5%:</b> <code>{usd_bcv_intervencion:,.2f}</code> $\n"
            f"   <i>(Tasa + 0.5%: {tasa_con_intervencion:,.3f} Bs/$)</i>\n\n"
            f"{e('CHINCHE', '💬')} Puedes escribir un nuevo monto en USDT directamente."
        )

        bot.answer_callback_query(call.id)
        msg_final = bot.send_message(
            call.message.chat.id,
            respuesta,
            parse_mode="HTML",
            reply_markup=obtener_teclado_calc()
        )
        bot.register_next_step_handler(msg_final, lambda m: procesar_calculo(m, modo="USDT_BS_USD"))

    @bot.callback_query_handler(func=lambda call: call.data == "calc_usdt_p2p_bdv")
    def callback_calc_usdt_bdv(call):
        user_id = call.from_user.id
        data = USER_CALC_DATA.get(user_id, {})
        tasa_bdv = data.get("tasa_p2p_bdv", 0.0)
        ejecutar_resultado_usdt_bs_usd(call, tasa_bdv, "BDV")

    @bot.callback_query_handler(func=lambda call: call.data == "calc_usdt_p2p_gen")
    def callback_calc_usdt_gen(call):
        user_id = call.from_user.id
        data = USER_CALC_DATA.get(user_id, {})
        tasa_gen = data.get("tasa_p2p_gen", 0.0)
        ejecutar_resultado_usdt_bs_usd(call, tasa_gen, "Monitor General")
        
