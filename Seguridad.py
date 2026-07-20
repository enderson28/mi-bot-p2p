# Palabras o frases clave que identifican los reportes de los Administradores
FRASES_PROHIBIDAS = [
    "monitor p2p",
    "calculadora de intervención",
    "tasas en tiempo real",
    "intervención bancaria"
]

def validar_copia_pega(bot, message, es_admin):
    """
    Si un usuario normal pega el texto del monitor o intervención en el chat,
    el bot borra el mensaje de inmediato para evitar desinformación o spam.
    """
    # Si es Administrador, lo dejamos hablar tranquilamente
    if es_admin:
        return False

    texto = message.text.lower() if message.text else ""
    
    # Verificamos si el mensaje contiene alguna de las frases clave del reporte oficial
    for frase in FRASES_PROHIBIDAS:
        if frase in texto:
            try:
                bot.delete_message(message.chat.id, message.message_id)
                print(f"🛡️ Copia no autorizada eliminada al usuario {message.from_user.id}")
                return True  # Mensaje borrado
            except Exception as e:
                print(f"⚠️ No se pudo borrar el copy-paste: {e}")
                return False
                
    return False
