from flask import Flask, request, jsonify, render_template
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
import email.utils
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor


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

@app.route('/prime')
def prime():
    return render_template('prime.html')
    
def revisar_cuenta(cuenta, palabra_clave, hace_15_min):
    try:
        print(f"🔍 Revisando cuenta: {cuenta['email']}")
        mail = imaplib.IMAP4_SSL(cuenta["imap"])
        mail.login(cuenta["email"], cuenta["password"])
        mail.select("inbox")

        result, data = mail.search(None, 'ALL')
        ids = data[0].split()
        ultimos_ids = ids[-10:]

        if not ids:
            mail.logout()
            return None

        for correo_id in reversed(ultimos_ids):
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
                soup = BeautifulSoup(cuerpo_html, 'html.parser')
                tabla_principal = soup.find('table')
                if tabla_principal:
                    for tag in tabla_principal.find_all(string=True):
                        if any(p in tag.lower() for p in ["centro de ayuda", "netflix te envió", "configuración de notificaciones"]):
                            tag.extract()
                    html_limpio = str(tabla_principal)
                else:
                    html_limpio = cuerpo_html

                mail.logout()
                return {
                    "asunto": asunto,
                    "remitente": remitente,
                    "fecha": fecha_raw,
                    "cuerpo_html": html_limpio,
                    "cuenta_encontrada": cuenta["email"]
                }

        mail.logout()
    except Exception as e:
        print(f"❌ Error con cuenta {cuenta['email']}: {e}")
    return None


@app.route('/buscar', methods=['POST'])
def buscar():
    palabra_clave = request.json.get('palabra')
    if not palabra_clave:
        return jsonify({'error': 'Palabra clave vacía'}), 400

    ahora = datetime.utcnow()
    hace_15_min = ahora - timedelta(minutes=15)

    with ThreadPoolExecutor() as executor:
        resultados = list(executor.map(lambda cuenta: revisar_cuenta(cuenta, palabra_clave, hace_15_min), CUENTAS))

    for resultado in resultados:
        if resultado:
            return jsonify({"correo": resultado})

    return jsonify({'mensaje': 'No se encontró ningún código reciente válido'}), 200
    
@app.route('/buscar_prime', methods=['POST'])
def buscar_prime():
    palabra_clave = request.json.get('palabra')
    if not palabra_clave:
        return jsonify({'error': 'Palabra clave vacía'}), 400

    ahora = datetime.utcnow()
    hace_15_min = ahora - timedelta(minutes=15)

    TITULOS_PRIME = [
        "Your Amazon verification code",
        "Amazon OTP",
        "Inicio de sesión en tu cuenta de Amazon",
        "Amazon security alert",
        "Tu código de verificación de Amazon",
        "Amazon authentication"
    ]

    def revisar_cuenta_prime(cuenta):
        try:
            mail = imaplib.IMAP4_SSL(cuenta["imap"])
            mail.login(cuenta["email"], cuenta["password"])
            mail.select("inbox")

            result, data = mail.search(None, 'ALL')
            ids = data[0].split()
            ultimos_ids = ids[-10:]

            for correo_id in reversed(ultimos_ids):
                result, msg_data = mail.fetch(correo_id, '(RFC822)')
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                asunto = decodificar_header(msg["Subject"] or "")
                destinatario = decodificar_header(msg["To"] or "").lower()

                if not any(titulo.lower() in asunto.lower() for titulo in TITULOS_PRIME):
                    continue
                if palabra_clave.lower() not in destinatario:
                    continue

                fecha_raw = msg["Date"]
                fecha_tuple = email.utils.parsedate_tz(fecha_raw)
                if fecha_tuple:
                    fecha_email = datetime.utcfromtimestamp(email.utils.mktime_tz(fecha_tuple))
                    if fecha_email < hace_15_min:
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
                    soup = BeautifulSoup(cuerpo_html, 'html.parser')
                    tabla = soup.find('table')
                    html_limpio = str(tabla) if tabla else cuerpo_html

                    mail.logout()
                    return {
                        "asunto": asunto,
                        "remitente": remitente,
                        "fecha": fecha_raw,
                        "cuerpo_html": html_limpio,
                        "cuenta_encontrada": cuenta["email"]
                    }

            mail.logout()
        except Exception as e:
            print(f"❌ Error con cuenta {cuenta['email']}: {e}")
        return None

    with ThreadPoolExecutor() as executor:
        resultados = list(executor.map(revisar_cuenta_prime, CUENTAS))

    for resultado in resultados:
        if resultado:
            return jsonify({"correo": resultado})

    return jsonify({'mensaje': 'No se encontró ningún código reciente válido'}), 200

if __name__ == '__main__':
    app.run(debug=True)
