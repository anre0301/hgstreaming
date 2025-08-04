from flask import Flask, request, jsonify, render_template
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
import email.utils

app = Flask(__name__)

CUENTAS = [
    {
        "email": "darienmurillodorsal@gmail.com",
        "password": "hwkjziivbocffrsw",
        "imap": "imap.gmail.com"
    },
    {
        "email": "albertcuarto349@gmail.com", 
        "password": "ctdfsnldmcauhnmx",
        "imap": "imap.gmail.com"
    }
]

TITULOS_VALIDOS = [
    "Tu código de acceso temporal de Netflix",
    "Importante: Cómo actualizar tu Hogar con Netflix",
    "Netflix: Nueva solicitud de inicio de sesión",
    "Completa tu solicitud de restablecimiento de contraseña"
]

def decodificar_header(texto):
    partes = decode_header(texto)
    resultado = ''
    for parte, codificacion in partes:
        if isinstance(parte, bytes):
            resultado += parte.decode(codificacion or 'utf-8', errors='ignore')
        else:
            resultado += parte
    return resultado

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/netflix')
def netflix():
    return render_template('netflix.html')

@app.route('/buscar', methods=['POST'])
def buscar():
    palabra_clave = request.json.get('palabra')
    if not palabra_clave:
        return jsonify({'error': 'Palabra clave vacía'}), 400

    ahora = datetime.utcnow()
    hace_15_min = ahora - timedelta(minutes=15)

    try:
        for cuenta in CUENTAS:
            try:
                mail = imaplib.IMAP4_SSL(cuenta["imap"])
                mail.login(cuenta["email"], cuenta["password"])
                mail.select("inbox")

                result, data = mail.search(None, 'ALL')
                ids = data[0].split()

                for correo_id in reversed(ids):
                    result, msg_data = mail.fetch(correo_id, '(RFC822)')
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    asunto = decodificar_header(msg["Subject"] or "")
                    destinatario = decodificar_header(msg["To"] or "").lower()

                    if asunto not in TITULOS_VALIDOS:
                        continue
                    if palabra_clave.lower() not in destinatario:
                        continue

                    fecha_raw = msg["Date"]
                    fecha_tuple = email.utils.parsedate_tz(fecha_raw)
                    if fecha_tuple:
                        fecha_email = datetime.utcfromtimestamp(email.utils.mktime_tz(fecha_tuple))
                        if fecha_email < hace_15_min:
                            continue
                    else:
                        continue

                    remitente = decodificar_header(msg["From"] or "")

                    cuerpo_html = None
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/html":
                                cuerpo_html = part.get_payload(decode=True).decode(errors="ignore")
                                break
                    elif msg.get_content_type() == "text/html":
                        cuerpo_html = msg.get_payload(decode=True).decode(errors="ignore")

                    if cuerpo_html:
                        mail.logout()
                        return jsonify({
                            "correo": {
                                "asunto": asunto,
                                "remitente": remitente,
                                "fecha": fecha_raw,
                                "cuerpo_html": cuerpo_html,
                                "cuenta_encontrada": cuenta["email"]
                            }
                        })

                mail.logout()

            except Exception as cuenta_error:
                print(f"Error con cuenta {cuenta['email']}: {cuenta_error}")
                continue

        return jsonify({'mensaje': 'No se encontró ningún código reciente válido'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
