# Ruta Residencias · Agenda de reparto

Mini agenda para organizar el reparto en residencias de ancianos y llevar el
control de cupones de pañales y otros productos.

## Qué incluye

- **Inicio**: siguiente parada recomendada, resumen del día y avisos de cupones.
- **Agenda semanal**: visitas por día, estados (pendiente, entregada, incidencia)
  y residencias que faltan por visitar esa semana.
- **Residencias**: fichas con zona, dirección, teléfono, horario, orden de ruta y
  visitas por semana.
- **Cupones**: stock por producto, cargas de cupones y cupones usados.
- **Visitas**: productos entregados, unidades, cupones gastados y notas.
- Diseño **mobile-first** pensado para usarlo desde el móvil.

## Reglas de cupones

- Cada producto define **cupones por unidad** (por defecto 1).
- Al cargar una visita, los cupones se calculan solos: `unidades × cupones por unidad`
  (puedes escribirlos a mano si lo necesitas).
- El stock de un producto = cupones cargados − cupones usados en visitas
  **entregadas**.
- Si borras una visita entregada, sus cupones vuelven al stock automáticamente.
- Cada producto tiene un **aviso de stock bajo** configurable.

## Puesta en marcha en local (Windows)

```powershell
# 1. Crear y activar el entorno virtual
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Instalar dependencias
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3. Base de datos y datos de ejemplo
python manage.py migrate
python manage.py seed_demo

# 4. Crear usuario para el panel de administración
python manage.py createsuperuser

# 5. Arrancar
python manage.py runserver
```

Abre <http://127.0.0.1:8000/> en el móvil o en el navegador. El panel de
administración está en <http://127.0.0.1:8000/admin/>.

> Si PowerShell bloquea el script de activación, ejecuta antes:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

## Subir a GitHub

```powershell
git init
git add .
git commit -m "Agenda de reparto en residencias"
git branch -M main
git remote add origin https://github.com/SistGoyPeru/agenda_residencia.git
git push -u origin main
```

## Desplegar en Render

1. Entra en <https://render.com> y conecta tu cuenta de GitHub.
2. **New → Blueprint** y elige el repositorio `agenda_residencia`.
   Render leerá `render.yaml` y creará la base de datos PostgreSQL y el servicio web.
3. Cuando termine el primer despliegue, abre la URL del servicio.
4. Para cargar datos de ejemplo o crear el administrador, abre **Shell** en el
   servicio de Render y ejecuta:
   ```bash
   python manage.py seed_demo
   python manage.py createsuperuser
   ```

También puedes crearlo a mano con **New → Web Service**:

- Build Command: `./build.sh`
- Start Command: `gunicorn config.wsgi:application`
- Variables: `DATABASE_URL` (la da Render), `SECRET_KEY` (genera una), `DEBUG=0`

## Variables de entorno

| Variable | Descripción |
| --- | --- |
| `SECRET_KEY` | Clave secreta de Django. Obligatoria en producción. |
| `DEBUG` | `1` en local, `0` en producción. |
| `DATABASE_URL` | Cadena de conexión PostgreSQL (Render la rellena sola). |
| `ALLOWED_HOSTS` | Hosts permitidos separados por comas. |
| `CSRF_TRUSTED_ORIGINS` | Orígenes de confianza separados por comas. |

En local puedes copiar `.env.example` a `.env`, pero el proyecto funciona sin
`.env` usando SQLite.
