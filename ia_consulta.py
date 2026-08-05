import os
import json
import requests
from datetime import datetime
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# Modelo en OpenRouter con mayor nivel de razonamiento y ultra económico
MODELO_IA = "openai/gpt-4o-mini"

# TU ID DE TELEGRAM (Como dueño no tendrás límite de preguntas)
# Puedes colocar tu ID numérico o el de varios administradores
ADMIN_IDS = [5073264705, 1676933074]  # <-- ⚠️ REEMPLAZA 123456789 POR TU ID REAL DE TELEGRAM

# Diccionarios globales en memoria
HISTORIAL_CHAT = {}
USO_DIARIO_USUARIOS = {}  # {user_id: {"fecha": "YYYY-MM-DD", "preguntas": int}}

def registrar_ia_consulta(bot, redis_client, obtener_teclado_func):
    """
    Registra el módulo interactivo de consulta Financiera con IA via OpenRouter.
    Mantiene el hilo conversacional, inyecta datos de Redis y limita el uso diario.
    """

    def solicitar_consulta_ia(message):
        """Punto de entrada al presionar el botón del menú"""
        if message.chat.type != "private":
            return

        chat_id = message.chat.id
        HISTORIAL_CHAT[chat_id] = []

        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(KeyboardButton("⬅️ Salir al menú"))

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
        """Procesa las preguntas manteniendo el historial y control de límites"""
        if message.chat.type != "private":
            return

        chat_id = message.chat.id
        user_id = message.from_user.id
        texto = message.text.strip() if message.text else ""

        # Opción de salida
        if texto == "⬅️ Salir al menú" or texto.startswith("/"):
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

        # -------------------------------------------------------------
        # 🛡️ CONTROL DE LÍMITE DIARIO DE PREGUNTAS (50 por usuario)
        # -------------------------------------------------------------
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")

        # Inicializar o reiniciar contador si es un nuevo día
        if user_id not in USO_DIARIO_USUARIOS or USO_DIARIO_USUARIOS[user_id]["fecha"] != fecha_hoy:
            USO_DIARIO_USUARIOS[user_id] = {"fecha": fecha_hoy, "preguntas": 0}

        # Verificar si superó el límite (Solo si NO es Administrador)
        if user_id not in ADMIN_IDS:
            if USO_DIARIO_USUARIOS[user_id]["preguntas"] >= 50:
                bot.send_message(
                    chat_id,
                    "⚠️ **Has alcanzado el límite diario de 50 consultas con la IA.**\n\n"
                    "Por favor, regresa mañana para continuar consultando o utiliza las herramientas del menú.",
                    parse_mode="Markdown"
                )
                bot.register_next_step_handler(message, procesar_consulta_ia)
                return

        # Incrementar contador de preguntas
        USO_DIARIO_USUARIOS[user_id]["preguntas"] += 1
        preguntas_usadas = USO_DIARIO_USUARIOS[user_id]["preguntas"]

        # Notificación visual
        msg_espera = bot.send_message(
            chat_id, 
            "🧠 *Analizando respuesta...*", 
            parse_mode="Markdown"
        )

        # -------------------------------------------------------------
        # 📊 OBTENER BCV TASA DESDE REDIS
        # -------------------------------------------------------------
        tasa_bcv = "No disponible"
        if redis_client:
            try:
                data_raw = redis_client.get("CACHE_TASAS_STORAGE")
                if data_raw:
                    data = json.loads(data_raw) if isinstance(data_raw, str) else json.loads(data_raw.decode('utf-8'))
                    tasa_bcv = data.get("bcv_tasa", "No disponible")
            except Exception as e:
                print(f"Error extrayendo tasa de Redis: {e}")

        # -------------------------------------------------------------
        # ⚙️ CONFIGURACIÓN DE PROMPT Y OPTIMIZACIÓN DE HILO
        # -------------------------------------------------------------
        system_prompt = (
            "Eres un asistente financiero y analista experto en arbitraje de criptomonedas y mercado P2P en Venezuela. "
            f"DATOS EN TIEMPO REAL: La tasa oficial BCV actual registrada en el sistema es: {tasa_bcv} VES/USD. "
            "INSTRUCCIONES DE RESPUESTA: Sé extremadamente directo, conciso y natural. "
            "Responde en máximo 2 o 3 párrafos o puntos breves. Evita explicaciones teóricas largas."
        )

        if chat_id not in HISTORIAL_CHAT:
            HISTORIAL_CHAT[chat_id] = []

        HISTORIAL_CHAT[chat_id].append({"role": "user", "content": texto})

        # ⚡ OPTIMIZACIÓN: Enviamos solo los últimos 8 mensajes (4 preguntas + 4 respuestas)
        # Esto ahorra hasta un 80% de tokens y evita respuestas lentas
        historial_reciente = HISTORIAL_CHAT[chat_id][-8:]
        messages_payload = [{"role": "system", "content": system_prompt}] + historial_reciente

        payload = {
            "model": MODELO_IA,
            "messages": messages_payload,
            "max_tokens": 300,
            "temperature": 0.5
        }

        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        headers = {
            "Authorization": f"Bearer {openrouter_key}",
            "Content-Type": "json/application" if False else "application/json"
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

                # Si no es admin, opcionalmente puedes agregar una nota al final con sus preguntas restantes
                # aviso_limite = f"\n\n_(Consulta {preguntas_usadas}/50 del día)_" if user_id not in ADMIN_IDS else ""
                # respuesta_ia += aviso_limite

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
    
