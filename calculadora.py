from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from emojis import TG_EMOJIS, e

def registrar_calculadora(bot, obtener_cache_func, obtener_teclado_func):
    """
    Registra el módulo de calculadora interactiva de divisas (USD -> Bs y Bs -> USD).
    """

    def obtener_teclado_calc():
        """Devuelve el teclado fijo inferior para la calculadora."""
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(
            KeyboardButton("💵 USD a 🇻🇪 Bs"),
            KeyboardButton("🇻🇪 Bs a 💵 USD")
        )
        markup.add(KeyboardButton("⬅️ Volver al menú"))
        return markup

    @bot.message_handler(func=lambda message: "Calculadora" in message.text if message.text else False)
    def solicitar_monto_mensaje(message, modo="USD_BS"):
        if message.chat.type != 'private':
            return

        # Limpiamos cualquier paso handler previo para evitar solapamientos
        bot.clear_step_handler_by_chat_id(message.chat.id)

        texto_indicacion = (
            f"<blockquote>{e('CALCULADORA', '📠')} CALCULADORA AUTOMÁTICA BCV (+0.5%)</blockquote>\n\n"
            f"{e('check', '✔️')} Modo actual: {e('DINERO', '💵')} {e('FLECHA_DERECHA', '➡️')} 🇻🇪 Bolívares\n"
            f"{e('clic', '🎯')} Escribe la cifra en (USD) directamente (Ejemplo: `5`, `12.5`, `100`):\n\n"
            f"{e('ARENITA', '⏳')} _Esperando tu monto..._\n"
        ) if modo == "USD_BS" else (
            f"<blockquote>{e('CALCULADORA', '📠')} CALCULADORA DIVISAS AL BCV (+0.5%)</blockquote>\n\n"
            f"{e('check', '✔️')} Modo actual: 🇻🇪 Bolívares {e('FLECHA_DERECHA', '➡️')} {e('DINERO', '💵')}\n"
            f"{e('clic', '🎯')} Escribe la cifra en (Bs) directamente (Ejemplo: `500`, `1500.50`):\n\n"
            f"{e('ARENITA', '⏳')} _Esperando tu monto..._\n"
        )

        msg = bot.send_message(
            message.chat.id,
            texto_indicacion,
            parse_mode="HTML",
            reply_markup=obtener_teclado_calc()
        )
        
        bot.register_next_step_handler(msg, lambda m: procesar_calculo(m, modo))

    def procesar_calculo(message, modo="USD_BS"):
        if message.chat.type != 'private':
            return

        texto = message.text.strip() if message.text else ""

        # 1. Opción de salida al menú principal
        if texto == "⬅️ Volver al menú" or texto.startswith("/"):
            bot.clear_step_handler_by_chat_id(message.chat.id)
            teclado_restablecido = obtener_teclado_func(message.from_user)
            bot.send_message(
                message.chat.id,
                "🏠 *Menú principal restablecido.*",
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
            

        # 3. Normalizar comas a puntos
        texto_limpio = texto.replace(",", ".")

        try:
            monto_entrada = float(texto_limpio)
            if monto_entrada <= 0:
                raise ValueError("Monto positivo requerido")
        except ValueError:
            msg_err = bot.send_message(
                message.chat.id,
                "⚠️ *Monto inválido.* Por favor escribe solo números (Ejemplo: `15` o `20.5`) "
                "o toca un botón de modo abajo.",
                parse_mode="Markdown",
                reply_markup=obtener_teclado_calc()
            )
            bot.register_next_step_handler(msg_err, lambda m: procesar_calculo(m, modo))
            return

        # 4. Obtener tasa BCV
        cache = obtener_cache_func()
        tasa_bcv = cache.get("bcv_tasa", 766.86)
        tasa_con_intervencion = tasa_bcv * 1.005

        # 5. Cálculo según el modo
        if modo == "USD_BS":
            monto_usd = monto_entrada
            monto_bolivares = monto_usd * tasa_con_intervencion
            
            respuesta = (
                f"<blockquote>{e('CONSULTA1', '🗯️')} RESULTADO DE CÁLCULO BCV</blockquote>\n\n"
                f"{e('DINERO', '💵')} Monto en USD: {monto_usd:,.2f}\n"
                f"{e('BCV', '👏')} Tasa BCV oficial: {tasa_bcv:,.2f} Bs.\n"
                f"<blockquote>{e('BALANZA', '⚖️')} Tasa + 0.5% : {tasa_con_intervencion:,.4f} Bs.</blockquote>\n\n"
                f"{e('pago_movil', '😶‍🌫️')} Total a pagar en Bolívares:\n"
                f"{e('FLECHA_DERECHA', '👏')} <code>{monto_bolivares:,.2f}</code> Bs.\n\n"
                f"{e('CHINCHE', '📌')} Puedes seguir escribiendo montos en $ o cambiar de modo abajo.\n"
                f"----------------------------------------------------------\n"
            )
        else: # Modo BS_USD (Inverso)
            monto_bolivares = monto_entrada
            monto_usd = monto_bolivares / tasa_con_intervencion
            
            respuesta = (
                f"<blockquote>{e('CONSULTA1', '🗯️')} RESULTADO DE CÁLCULO DIVISAS AL BCV</blockquote>\n\n"
                f"🇻🇪 Monto disponible en Bs: {monto_bolivares:,.2f} Bs.\n"
                f"{e('BCV', '👏')} Tasa BCV oficial: {tasa_bcv:,.2f} Bs.\n"
                f"<blockquote>{e('BALANZA', '⚖️')} Tasa + 0.5% : <code>{tasa_con_intervencion:,.4f}</code> Bs.</blockquote>\n\n"
                f"{e('DINERO', '💵')} Puedes comprar un total de:\n"
                f"{e('FLECHA_DERECHA', '➡️')} <code>{monto_usd:,.2f}</code> USD\n\n"
                f"{e('CHINCHE', '📌')} Puedes seguir escribiendo montos en Bs o cambiar de modo abajo.\n"
                f"----------------------------------------------------------\n"
            )

        # 6. Enviar respuesta y mantener escucha para el siguiente número
        msg_res = bot.send_message(
            message.chat.id,
            respuesta,
            parse_mode="HTML",
            reply_markup=obtener_teclado_calc()
        )

        bot.register_next_step_handler(msg_res, lambda m: procesar_calculo(m, modo))
        
