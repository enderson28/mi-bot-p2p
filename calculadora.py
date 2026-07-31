from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def registrar_calculadora(bot, obtener_cache_func, funcion_menu_principal=None):
    """
    Registra los manejadores para la calculadora de divisas BCV + 0.5%.
    """

    def solicitar_monto(call):
        """Paso 1: Se activa al presionar el botón de texto '📟 Calculadora'"""
        chat_id = call.message.chat.id

        # Garantizar que solo funcione en chat privado
        if call.message.chat.type != 'private':
            return

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⬅️ Volver al menú", callback_data="volver_menu_principal"))

        # Usamos send_message porque proviene de un ReplyKeyboardMarkup (teclado de texto)
        msg = bot.send_message(
            chat_id,
            "📟 *CALCULADORA AUTOMÁTICA BCV (+0.5% Intervención)*\n\n"
            "¿Cuántos USD deseas calcular?\n"
            "Escribe la cifra directamente en el chat (Ejemplo: `5`, `12.5`, `30`, `500`):\n\n"
            "_Esperando tu monto..._",
            parse_mode="Markdown",
            reply_markup=markup
        )

        # Escuchar únicamente el siguiente mensaje de este usuario
        bot.register_next_step_handler(msg, procesar_calculo)

    def procesar_calculo(message):
        """Paso 2: Procesa la cifra introducida por el usuario"""
        if message.chat.type != 'private':
            return

        texto = message.text.strip() if message.text else ""

        # Si el usuario presiona un comando o un botón del menú mientras esperaba el monto, no rompe el flujo
        if texto.startswith("/") or texto in ["🟢 P2P-USDT 🔴", "📊 Intervencion 📊", "📟 Calculadora", "📜 Regla de Oro", "🔶 BPay 🔶", "🔵 GPay 🔵", "⚙️ Soporte"]:
            return

        # Normalizar separadores decimales (ejemplo 12,5 a 12.5)
        texto_limpio = texto.replace(",", ".")
        
        try:
            monto_usd = float(texto_limpio)
            if monto_usd <= 0:
                raise ValueError("Monto debe ser positivo")
        except ValueError:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔄 Intentar de nuevo", callback_data="abrir_calculadora"))
            markup.add(InlineKeyboardButton("⬅️ Volver al menú", callback_data="volver_menu_principal"))
            
            bot.send_message(
                message.chat.id,
                "⚠️ *Monto inválido.* Por favor escribe solo números (Ejemplo: `15` o `20.5`).",
                parse_mode="Markdown",
                reply_markup=markup
            )
            return

        # Obtener la tasa BCV del cache global / Redis
        cache = obtener_cache_func()
        tasa_bcv = cache.get("bcv_tasa", 745.64)
        tasa_con_intervencion = tasa_bcv * 1.005  # Tasa BCV + 0.5%
        monto_bolivares = monto_usd * tasa_con_intervencion

        respuesta = (
            f"📊 *RESULTADO DE CÁLCULO BCV*\n\n"
            f"💵 *Monto en USD:* `${monto_usd:,.2f}`\n"
            f"🏛️ *Tasa BCV oficial:* `{tasa_bcv:,.2f} Bs.`\n"
            f"➕ *Tasa + 0.5% Intervención:* `{tasa_con_intervencion:,.4f} Bs.`\n\n"
            f"💳 *Total a pagar en Bolívares:*\n"
            f"👉 *`{monto_bolivares:,.2f} Bs.`*\n\n"
            f"_Cálculo basado en la tasa oficial del día._"
        )

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔄 Calcular otro monto", callback_data="abrir_calculadora"))

        bot.send_message(
            message.chat.id,
            respuesta,
            parse_mode="Markdown",
            reply_markup=markup
        )

    return solicitar_monto
