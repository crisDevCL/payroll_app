from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import os
import json
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from pypdf import PdfReader, PdfWriter
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'payroll_secret_key_2024'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

# Admin credentials
ADMIN_USER = 'cristian_admin'
ADMIN_PASS = '$Cris.dev.2026#'

# Email config file
CONFIG_FILE = 'email_config.json'
RECIPIENTS_FILE = 'recipients.json'

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {'smtp_server': 'smtp.gmail.com', 'smtp_port': 587, 'email': '', 'password': '', 'subject': 'Liquidación de Sueldo', 'body': 'Estimado trabajador,\n\nAdjunto encontrará su liquidación de sueldo.\n\nSaludos cordiales,\nRecursos Humanos'}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def load_recipients():
    if os.path.exists(RECIPIENTS_FILE):
        with open(RECIPIENTS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_recipients(recipients):
    with open(RECIPIENTS_FILE, 'w') as f:
        json.dump(recipients, f)

@app.route('/', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
    error = None
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USER and request.form['password'] == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            error = 'Credenciales incorrectas. Acceso denegado.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    recipients = load_recipients()
    return render_template('dashboard.html', recipients=recipients)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    config = load_config()
    if request.method == 'POST':
        config['smtp_server'] = request.form['smtp_server']
        config['smtp_port'] = int(request.form['smtp_port'])
        config['email'] = request.form['email']
        if request.form['password']:
            config['password'] = request.form['password']
        config['subject'] = request.form['subject']
        config['body'] = request.form['body']
        save_config(config)
        flash('Configuración guardada exitosamente.')
    return render_template('settings.html', config=config)

@app.route('/recipients', methods=['GET', 'POST'])
def recipients():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    recs = load_recipients()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            new = {'name': request.form['name'], 'email': request.form['email'], 'page': int(request.form['page'])}
            recs.append(new)
            save_recipients(recs)
            flash(f'Trabajador {new["name"]} agregado.')
        elif action == 'delete':
            idx = int(request.form['index'])
            recs.pop(idx)
            save_recipients(recs)
            flash('Trabajador eliminado.')
        elif action == 'import_csv':
            file = request.files.get('csv_file')
            if file:
                content = file.read().decode('utf-8')
                lines = content.strip().split('\n')
                added = 0
                for line in lines[1:]:  # skip header
                    parts = line.strip().split(',')
                    if len(parts) >= 3:
                        recs.append({'name': parts[0].strip(), 'email': parts[1].strip(), 'page': int(parts[2].strip())})
                        added += 1
                save_recipients(recs)
                flash(f'{added} trabajadores importados.')
    return render_template('recipients.html', recipients=recs)

@app.route('/process', methods=['POST'])
def process():
    if not session.get('logged_in'):
        return jsonify({'error': 'No autorizado'}), 401

    if 'pdf_file' not in request.files:
        return jsonify({'error': 'No se adjuntó archivo'}), 400

    file = request.files['pdf_file']
    if file.filename == '':
        return jsonify({'error': 'Archivo vacío'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Split PDF
    reader = PdfReader(filepath)
    total_pages = len(reader.pages)
    recipients = load_recipients()
    config = load_config()

    results = []
    errors = []

    # Clear output folder
    for f in os.listdir(app.config['OUTPUT_FOLDER']):
        os.remove(os.path.join(app.config['OUTPUT_FOLDER'], f))

    # Generate individual PDFs
    page_files = {}
    for i in range(total_pages):
        writer = PdfWriter()
        writer.add_page(reader.pages[i])
        out_path = os.path.join(app.config['OUTPUT_FOLDER'], f'liquidacion_pagina_{i+1}.pdf')
        with open(out_path, 'wb') as f:
            writer.write(f)
        page_files[i+1] = out_path

    # Send emails
    def send_emails():
        try:
            server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
            server.starttls()
            server.login(config['email'], config['password'])

            for rec in recipients:
                page_num = rec.get('page')
                if page_num and page_num in page_files:
                    msg = MIMEMultipart()
                    msg['From'] = config['email']
                    msg['To'] = rec['email']
                    msg['Subject'] = config['subject']
                    msg.attach(MIMEText(f"Estimado/a {rec['name']},\n\n{config['body']}", 'plain'))

                    with open(page_files[page_num], 'rb') as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition', f'attachment; filename=liquidacion_{rec["name"].replace(" ", "_")}.pdf')
                        msg.attach(part)

                    server.sendmail(config['email'], rec['email'], msg.as_string())
                    results.append({'name': rec['name'], 'email': rec['email'], 'status': 'enviado'})
                else:
                    errors.append({'name': rec['name'], 'email': rec['email'], 'status': 'página no encontrada'})

            server.quit()
        except Exception as e:
            errors.append({'error': str(e)})

    thread = threading.Thread(target=send_emails)
    thread.start()
    thread.join(timeout=60)

    return jsonify({
        'total_pages': total_pages,
        'recipients_count': len(recipients),
        'results': results,
        'errors': errors
    })

@app.route('/download-csv-template')
def download_csv_template():
    from flask import Response
    content = "nombre,email,pagina\nJuan Pérez,juan@empresa.com,1\nMaría López,maria@empresa.com,2\n"
    return Response(content, mimetype='text/csv',
                    headers={"Content-Disposition": "attachment;filename=plantilla_trabajadores.csv"})

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('output', exist_ok=True)
    app.run(debug=True, port=5000)
