from flask import Flask, request, jsonify, render_template
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
import email.utils
from bs4 import BeautifulSoup

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
    "Completa tu solicitud de restablecimiento de contraseña",
    "Netflix: Tu código de inicio de sesión"
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
            print(f"🔍 Revisando cuenta: {cuenta['email']}")
            try:
                mail = imaplib.IMAP4_SSL(cuenta["imap"])
                mail.login(cuenta["email"], cuenta["password"])
                mail.select("inbox")

                result, data = mail.search(None, 'ALL')
                ids = data[0].split()
                ultimos_ids = ids[-5:]

                if not ids:
                    print(f"📭 No hay correos en {cuenta['email']}")
                    mail.logout()
                    continue

                for correo_id in reversed(ultimos_ids):
                    result, msg_data = mail.fetch(correo_id, '(RFC822)')
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    asunto = decodificar_header(msg["Subject"] or "")
                    destinatario = decodificar_header(msg["To"] or "").lower()

                    print(f"✉️ Asunto: {asunto} | Para: {destinatario}")

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
                        # 🧼 Limpiar HTML para extraer solo la parte útil
                        soup = BeautifulSoup(cuerpo_html, 'html.parser')
                        tabla_principal = soup.find('table')

                        if tabla_principal:
                            for tag in tabla_principal.find_all(string=True):
                                if any(p in tag.lower() for p in ["centro de ayuda", "netflix te envió", "configuración de notificaciones"]):
                                    tag.extract()
                            html_limpio = str(tabla_principal)
                        else:
                            html_limpio = cuerpo_html

                        print(f"✅ Código encontrado en: {cuenta['email']}")
                        mail.logout()
                        return jsonify({
                            "correo": {
                                "asunto": asunto,
                                "remitente": remitente,
                                "fecha": fecha_raw,
                                "cuerpo_html": html_limpio,
                                "cuenta_encontrada": cuenta["email"]
                            }
                        })

                mail.logout()

            except Exception as cuenta_error:
                print(f"❌ Error con cuenta {cuenta['email']}: {cuenta_error}")
                continue

        print("🔴 No se encontró ningún código válido en ninguna cuenta.")
        return jsonify({'mensaje': 'No se encontró ningún código reciente válido'}), 200

    except Exception as e:
        print("🚨 Error general:", str(e))
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
