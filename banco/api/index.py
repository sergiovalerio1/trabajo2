import hmac
import logging
import os
import secrets
import sys
from decimal import Decimal, InvalidOperation

# Permite importar servicios.py (está en la raíz, un nivel arriba de /api)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

from servicios import CServicios

try:  # solo para desarrollo local; en Vercel las variables ya existen
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except ImportError:
    pass

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))


class QuitarPrefijo:
    """Si Vercel entrega /api/index/login, lo deja como /login."""
    PREFIJOS = ("/api/index.py", "/api/index")

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        ruta = environ.get("PATH_INFO", "")
        for p in self.PREFIJOS:
            if ruta == p or ruta.startswith(p + "/"):
                environ["PATH_INFO"] = ruta[len(p):] or "/"
                break
        return self.wsgi_app(environ, start_response)


app.wsgi_app = QuitarPrefijo(app.wsgi_app)

# ---------------------------------------------------------------- configuración
app.secret_key = os.environ.get("SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("La variable de entorno SECRET_KEY no está definida.")

# Credenciales del cajero (la tabla 'ahorros' solo tiene id, saldo y ahorro,
# por eso el acceso al banco se define aquí y no en la base de datos).
BANCO_USUARIO = os.environ.get("BANCO_USUARIO")
BANCO_CLAVE = os.environ.get("BANCO_CLAVE")
if not BANCO_USUARIO or not BANCO_CLAVE:
    raise RuntimeError("Faltan las variables de entorno BANCO_USUARIO y BANCO_CLAVE.")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.environ.get("VERCEL")),  # HTTPS solo en Vercel
)

servicios = CServicios()
log = logging.getLogger(__name__)

MAX_VALOR = Decimal("999999999999.99")  # NUMERIC(14,2)


# ---------------------------------------------------------------- utilidades
def _token_csrf():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


app.jinja_env.globals["csrf_token"] = _token_csrf


@app.template_filter("moneda")
def moneda(valor):
    return "$\u00a0{:,.2f}".format(Decimal(str(valor)))  # espacio no separable: no se parte en 2 líneas


@app.before_request
def proteger_csrf():
    if request.method == "POST":
        enviado = request.form.get("csrf", "")
        esperado = session.get("csrf", "")
        if not esperado or not hmac.compare_digest(enviado, esperado):
            abort(400, "Formulario vencido. Recarga la página e inténtalo de nuevo.")


def _igual(a, b):
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def _leer_valor(texto):
    """Convierte el texto del formulario en Decimal válido (o None)."""
    try:
        valor = Decimal(texto.strip())
    except (InvalidOperation, AttributeError):
        return None
    if not valor.is_finite() or valor <= 0 or valor > MAX_VALOR:
        return None
    if valor != valor.quantize(Decimal("0.01")):  # máximo 2 decimales
        return None
    return valor


# ---------------------------------------------------------------- rutas
@app.route("/")
def index():
    if not session.get("cajero"):
        return redirect(url_for("login"))
    ultimo = session.pop("ultimo", None)  # resultado de la última operación
    return render_template("index.html", cajero=session["cajero"], ultimo=ultimo)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        clave = request.form.get("clave", "")
        if _igual(usuario, BANCO_USUARIO) and _igual(clave, BANCO_CLAVE):
            session.clear()
            session["cajero"] = usuario
            return redirect(url_for("index"))
        flash("Usuario o contraseña incorrectos.", "error")
        return redirect(url_for("login"))

    if session.get("cajero"):
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/ahorrar", methods=["POST"])
def ahorrar():
    if not session.get("cajero"):
        return redirect(url_for("login"))

    id_cliente = request.form.get("id_cliente", "").strip()
    texto_valor = request.form.get("valor", "")

    if not id_cliente or len(id_cliente) > 20:
        flash("Ingresa un id de cliente válido (máx. 20 caracteres).", "error")
        return redirect(url_for("index"))

    valor = _leer_valor(texto_valor)
    if valor is None:
        flash("Ingresa un valor mayor que cero, con máximo 2 decimales.", "error")
        return redirect(url_for("index"))

    try:
        r = servicios.ahorrar(id_cliente, valor)
    except Exception:
        log.exception("Error llamando a sp_ahorrar")
        flash("No se pudo completar la operación. Intenta de nuevo.", "error")
        return redirect(url_for("index"))

    codigo = r["codigo"]
    if codigo == "OK":
        flash(f"Listo: {moneda(valor)} pasaron del saldo al ahorro del cliente {id_cliente}.", "exito")
    elif codigo == "SIN_SALDO":
        flash(f"El cliente {id_cliente} no tiene saldo disponible (saldo en $ 0.00). "
              "No se puede ahorrar.", "aviso")
    elif codigo == "SALDO_INSUFICIENTE":
        flash(f"El valor ({moneda(valor)}) es mayor que el saldo disponible "
              f"({moneda(r['saldo'])}).", "error")
    elif codigo == "NO_EXISTE":
        flash(f"No existe ningún cliente con el id {id_cliente}.", "error")
    else:
        flash("El valor ingresado no es válido.", "error")

    if r["saldo"] is not None:  # el cliente existe: mostrar su estado actual
        session["ultimo"] = {
            "id": id_cliente,
            "codigo": codigo,
            "valor": str(valor),
            "saldo": str(r["saldo"]),
            "ahorro": str(r["ahorro"]),
        }
    return redirect(url_for("index"))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.", "exito")
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
