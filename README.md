# PayrollOS — Sistema de Distribución de Liquidaciones

## Descripción
Aplicación web Flask para gestionar y distribuir liquidaciones de sueldo por correo electrónico de forma automática.

## Características
- 🔐 Login seguro (solo admin)
- 📄 Carga de PDF con todas las liquidaciones
- ✂️ Separación automática por página (1 página = 1 trabajador)
- 📧 Envío masivo de correos con PDF adjunto individual
- 👥 Gestión de trabajadores (agregar, eliminar, importar CSV)
- ⚙️ Configuración SMTP flexible (Gmail, Outlook, etc.)

## Instalación

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Ejecutar la aplicación
python app.py
```

Abrir en navegador: http://localhost:5000

## Credenciales por defecto
- Usuario: `admin`
- Contraseña: `admin123`

⚠️ Cambia las credenciales en `app.py` antes de usar en producción.

## Flujo de uso

1. **Configurar email SMTP** → Menú "Configuración Email"
   - Para Gmail: usa una "Contraseña de Aplicación"
   
2. **Agregar trabajadores** → Menú "Trabajadores"
   - Nombre, email, y número de página que les corresponde en el PDF
   - O importar desde CSV (nombre, email, pagina)

3. **Procesar nómina** → Dashboard
   - Subir el PDF con todas las liquidaciones
   - Clic en "Separar y Enviar Liquidaciones"
   - El sistema separa por página y envía cada una al correo correspondiente

## Estructura del CSV de importación
```
nombre,email,pagina
Juan Pérez,juan@empresa.com,1
María López,maria@empresa.com,2
Carlos Ruiz,carlos@empresa.com,3
```

## Seguridad
- Cambiar `app.secret_key` en producción
- Cambiar credenciales de admin
- Usar HTTPS en producción (nginx + certbot)
- Las contraseñas SMTP se guardan en `email_config.json` — proteger este archivo
