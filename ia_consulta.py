import os
import json
import requests
from datetime import datetime, timedelta
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# Modelo en OpenRouter con mayor nivel de razonamiento y ultra económico
MODELO_IA = "openai/gpt-4o-mini"

# ID DEL CREADOR / ADMINISTRADORES (Sin límites ni restricciones)
ADMIN_IDS = [5073264705, 1676933074]

# Diccionarios globales en memoria
HISTORIAL_CHAT = {}
# Estructura: {user_id: {"fecha": "YYYY-MM-DD", "preguntas": int}}
USO_DIARIO_USUARIOS = {}
# Registro del cupo global: {"fecha": "YYYY-MM-DD", "usuarios_registrados": set(user_ids)}
REGISTRO_CUPO_DIARIO = {"fecha": "", "usuarios_registrados": set()}


def registrar_ia_consulta(bot, redis_client, obtener_teclado_func):
    """
    Registra el módulo interactivo de consulta Financiera con IA via OpenRouter.
    Incluye rotación diaria, límite de 100 usuarios globales y comando /ia para el creador.
    """

    # ---------------------------------------------------------
    # HANDLER PARA EL COMANDO /ia (EXCLUSIVO CREADOR / ADMINS)
    # ---------------------------------------------------------
    @bot.message_handler(commands=['ia'])
    def publicar_anuncio_ia(message):
        user_id = message.from_user.id
        
        # Validación: Solo el Creador / Admins pueden ejecutar este comando
        if user_id not in ADMIN_IDS:
            return  # Ignorar silenciosamente si es un usuario común

        anuncio = (
            "🤖 **SERVICIO DE CONSULTA IA FINANCIERA** 🤖\n\n"
            "📢 *Estimada comunidad,* para mantener este servicio gratuito, rápido y sostenible, "
            "el módulo de IA opera bajo los siguientes parámetros en privado:\n\n"
            "✅ **Cupo Global:** 100 usuarios diarios.\n"
            "⛔ **Límite Individual:** 30 consultas por usuario en su día de acceso.\n"
            "🔁 **Rotación Equitativa:** Si usas la IA hoy, se activará un día de descanso para ti mañana, "
            "permitiendo que otros miembros del canal puedan consultar.\n"
            "♻️ **Actualización:** Datos en tiempo real de la tasa oficial del BCV.\n\n"
            "⚡ *¡Ingresa al bot en privado y presiona el botón **🤖 IA Consulta** para iniciar!*"
        )

        bot.send_message(
            message.chat.id,
            anuncio,
            parse_mode="Markdown"
        )

    # ---------------------------------------------------------
    # FLUJO EN PRIVADO
    # ---------------------------------------------------------
    def solicitar_consulta_ia(message):
        """Punto de entrada al presionar el botón del menú"""
        if message.chat.type != "private":
            return

        chat_id = message.chat.id
        HISTORIAL_CHAT[chat_id] = []

        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(KeyboardButton("🔙 Salir al menú"))

        msg = bot.send_message(
            chat_id,
            "🤖 **CONSULTA CON IA FINANCIERA**\n\n"
            "Haz tus preguntas sobre el mercado P2P, arbitraje, tasas y estrategias.\n\n"
            "⏳ *Esperando tu consulta...*",
            parse_mode="Markdown",
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, procesar_consulta_ia)

    def procesar_consulta_ia(message):
        """Procesa las preguntas manteniendo el historial y control de límites estritos"""
        if message.chat.type != "private":
            return

        chat_id = message.chat.id
        user_id = message.from_user.id
        texto = message.text.strip() if message.text else ""

        # Opción de salida
        if texto == "🔙 Salir al menú" or texto.startswith("/"):
            if chat_id in HISTORIAL_CHAT:
                del HISTORIAL_CHAT[chat_id]

            teclado_restablecido = obtener_teclado_func(message.from_user)
            bot.send_message(
                chat_id,
                "💡 *Menú principal restablecido.*",
                parse_mode="Markdown",
                reply_markup=teclado_restablecido
            )
            return

        # ---------------------------------------------------------
        # CONTROL DE ACCESO, CUPO Y DÍA INTERMEDIO (Solo si NO es Admin)
        # ---------------------------------------------------------
        fecha_hoy_dt = datetime.now()
        fecha_hoy = fecha_hoy_dt.strftime("%Y-%m-%d")
        fecha_ayer = (fecha_hoy_dt - timedelta(days=1)).strftime("%Y-%m-%d")

        if user_id not in ADMIN_IDS:
            # 1. Resetear el registro global si es un nuevo día
            if REGISTRO_CUPO_DIARIO["fecha"] != fecha_hoy:
                REGISTRO_CUPO_DIARIO["fecha"] = fecha_hoy
                REGISTRO_CUPO_DIARIO["usuarios_registrados"] = set()

            # 2. Control de Día Intermedio (Cooldown de 24h)
            # Si el usuario ya usó el servicio AYER, hoy le toca descanso
            if user_id in USO_DIARIO_USUARIOS:
                ultima_fecha_uso = USO_DIARIO_USUARIOS[user_id].get("fecha")
                if ultima_fecha_uso == fecha_ayer:
                    bot.send_message(
                        chat_id,
                        "⏳ **Día de rotación activo**\n\n"
                        "Ayer utilizaste el módulo de IA. Para permitir que otros miembros de la comunidad "
                        "puedan consultar, hoy es tu día de 😴 descanso.\n\n"
                        "🔄 *Podrás volver a consultar 👏🏽 mañana.*",
                        parse_mode="Markdown"
                    )
                    bot.register_next_step_handler(message, procesar_consulta_ia)
                    return

            # 3. Control del Cupo Global (Máximo 100 usuarios por día)
            if user_id not in REGISTRO_CUPO_DIARIO["usuarios_registrados"]:
                if len(REGISTRO_CUPO_DIARIO["usuarios_registrados"]) >= 100:
                    bot.send_message(
                        chat_id,
                        "🚫 **Cupo diario alcanzado**\n\n"
                        "Los 100 cupos diarios para consultas de IA ya han sido tomados hoy por otros usuarios.\n\n"
                        "⏰ *Por favor, intenta nuevamente mañana a primera hora.*",
                        parse_mode="Markdown"
                    )
                    bot.register_next_step_handler(message, procesar_consulta_ia)
                    return
                else:
                    # Registrar usuario en el cupo global del día
                    REGISTRO_CUPO_DIARIO["usuarios_registrados"].add(user_id)

            # 4. Inicializar o Resetear contador individual si es un nuevo día
            if user_id not in USO_DIARIO_USUARIOS or USO_DIARIO_USUARIOS[user_id]["fecha"] != fecha_hoy:
                USO_DIARIO_USUARIOS[user_id] = {"fecha": fecha_hoy, "preguntas": 0}

            # 5. Verificar Límite Individual de 30 Preguntas
            if USO_DIARIO_USUARIOS[user_id]["preguntas"] >= 30:
                bot.send_message(
                    chat_id,
                    "⚠️ **Has alcanzado el límite diario de 30 consultas con la IA.**\n\n"
                    "Por favor, regresa pasado mañana para continuar o utiliza las herramientas del menú.",
                    parse_mode="Markdown"
                )
                bot.register_next_step_handler(message, procesar_consulta_ia)
                return

            # Incrementar contador si pasa todas las validaciones
            USO_DIARIO_USUARIOS[user_id]["preguntas"] += 1
            preguntas_usadas = USO_DIARIO_USUARIOS[user_id]["preguntas"]
        else:
            preguntas_usadas = 0  # Para Admins no aplica conteo

        # Notificación visual
        msg_espera = bot.send_message(
            chat_id,
            "🧠 *Analizando respuesta...*",
            parse_mode="Markdown"
        )

        # ---------------------------------------------------------
        # OBTENER BCV TASA DESDE REDIS
        # ---------------------------------------------------------
        tasa_bcv = "No disponible"
        if redis_client:
            try:
                data_raw = redis_client.get("CACHE_TASAS_STORAGE")
                if data_raw:
                    dato = json.loads(data_raw) if isinstance(data_raw, str) else json.loads(data_raw.decode('utf-8'))
                    tasa_bcv = dato.get("bcv_tasa", "No disponible")
            except Exception as e:
                print(f"Error extrayendo tasa de Redis: {e}")

        # ---------------------------------------------------------
        # CONFIGURACIÓN DE PROMPT Y OPTIMIZACIÓN
        # ---------------------------------------------------------
        system_prompt = (
            f"Eres un asistente financiero y analista experto en arbitraje de criptomonedas y mercado P2P en Venezuela. "
            f"DATOS EN TIEMPO REAL: La tasa oficial BCV actual registrada en el sistema es: {tasa_bcv} Bs/USD. "
            f"INSTRUCCIONES DE RESPUESTA: Sé extremadamente directo, conciso y natural. "
            f"REGLA MATEMÁTICA OBLIGATORIA: Si realizas cálculos numéricos o porcentuales, verifica la precisión matemática paso a paso antes de escribir el resultado final. "
            f"Responde en máximo 30 líneas o puntos breves. Evita explicaciones teóricas innecesarias."
        )

        if chat_id not in HISTORIAL_CHAT:
            HISTORIAL_CHAT[chat_id] = []

        HISTORIAL_CHAT[chat_id].append({"role": "user", "content": texto})

        # OPTIMIZACIÓN: Enviamos solo los últimos 8 mensajes (4 preguntas + 4 respuestas)
        historial_reciente = HISTORIAL_CHAT[chat_id][-8:]
        messages_payload = [{"role": "system", "content": system_prompt}] + historial_reciente

        payload = {
            "model": MODELO_IA,
            "messages": messages_payload,
            "max_tokens": 500,
            "temperature": 0.3
        }

        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        headers = {
            "Authorization": f"Bearer {openrouter_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=20
            )
            data = response.json()

            if response.status_code == 200 and "choices" in data:
                respuesta_ia = data["choices"][0]["message"]["content"]
                HISTORIAL_CHAT[chat_id].append({"role": "assistant", "content": respuesta_ia})

                # Pie de página dinámico con emojis
                if user_id not in ADMIN_IDS:
                    restantes = 30 - preguntas_usadas
                    pie_pagina = f"\n\n───\n📊 *Uso diario:* `{preguntas_usadas}/30` consultas | ⚡ *Restantes hoy:* `{restantes}`"
                    respuesta_ia += pie_pagina
            else:
                print(f"⚠️ Error OpenRouter [{response.status_code}]: {data}")
                respuesta_ia = "⚠️ Ocurrió un inconveniente al obtener la respuesta del modelo de IA."

        except Exception as e:
            print(f"⚠️ Excepción HTTP: {e}")
            respuesta_ia = "⚠️ Error de conexión con el servicio de IA."

        # Borrar mensaje "Analizando..." y enviar respuesta
        try:
            bot.delete_message(chat_id, msg_espera.message_id)
        except Exception:
            pass

        bot.send_message(chat_id, f"🤖 **Respuesta:**\n\n{respuesta_ia}", parse_mode="Markdown")

        # Seguir escuchando para mantener la conversación
        bot.register_next_step_handler_by_chat_id(chat_id, procesar_consulta_ia)

    return solicitar_consulta_ia
    
