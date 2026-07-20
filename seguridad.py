# Lista de frases clave para detectar copias de mensajes oficiales del bot
FRASES_PROHIBIDAS = [
    # Reportes y Monitores Oficiales
    "monitor de tasas",
    "vigencia bcv",
    "bcv oficial",
    "calculadora de intervención",
    "intervención bancaria",
    "spread:",
    
    # Mensaje de invitación (/bot) y mensajes automáticos
    "aprovecha al máximo las herramientas del bot",
    "consulta en privado sin límites",
    
    # Mensaje automático de 6 horas (anuncios.py)
    "consulta las tasas y guías en privado",
    "para mantener el grupo libre de spam",
    
    # Avisos de restricción y autoría
    "comando exclusivo para administradores",
    "comando exclusivo del creador del bot"
]

def validar_copia_pega(bot, message, es_admin):
    """
    Si un usuario normal pega cualquier texto oficial del bot o sus reportes,
    el bot borra el mensaje de inmediato para evitar spam o confusión.
    """
    # Si es Administrador, lo dejamos hablar tranquilamente
    if es_admin:
        return False

    texto = message.text.lower() if message.text else ""
    
    # Verificamos si el mensaje contiene alguna de las frases prohibidas
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
    
