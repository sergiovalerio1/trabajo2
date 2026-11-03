import hmac
import logging
import os
import re
import sys
from decimal import Decimal, InvalidOperation

# Permite importar servicios.py (está en la raíz, un nivel arriba de /api)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from flask import Flask, flash, redirect, render_template, request, session, url_for

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

app.secret_key = os.environ.get("SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("La variable de entorno SECRET_KEY no está definida.")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.environ.get("VERCEL")),  # HTTPS solo en Vercel
)

# Credenciales para entrar a la app. La base de datos solo tiene la tabla
# "ahorros", así que el usuario y la clave de la app viven en variables de
# entorno. Si no las defines, se usan estas de demostración.
USUARIO_APP = os.environ.get("APP_USUARIO", "sergio")
CLAVE_APP = os.environ.get("APP_CLAVE", "banco2026")

ID_MAXIMO = 2_147_483_647          # máximo de una columna INTEGER
VALOR_MAXIMO = Decimal("999999999999.99")  # máximo de NUMERIC(14,2)

servicios = CServicios()
log = logging.getLogger(__name__)


# ---------------------------------------------------------------- utilidades

def formato_moneda(valor):
    """1250000 -> '$ 1.250.000'   |   1250.5 -> '$ 1.250,50'"""
    if valor is None:
        return "$ 0"
    v = Decimal(str(valor))
    entero, _, decimales = f"{v:.2f}".partition(".")
    texto = f"{int(entero):,}".replace(",", ".")
    if decimales != "00":
        texto += "," + decimales
    return "$ " + texto


app.jinja_env.filters["moneda"] = formato_moneda


def parsear_valor(texto):
    """Convierte lo que escribe la persona en Decimal. Devuelve None si no es válido.

    Entiende 50000, 50.000, 50,000, 50.000,50 y 50000.5
    (un solo separador con exactamente 3 dígitos después se toma como miles).
    """
    t = (texto or "").replace("$", "").replace(" ", "").replace(" ", "")
    if not t or not re.fullmatch(r"[0-9.,]+", t):
        return None

    if "." in t and "," in t:
        decimal = "." if t.rfind(".") > t.rfind(",") else ","
        miles = "," if decimal == "." else "."
        t = t.replace(miles, "").replace(decimal, ".")
    elif "." in t or "," in t:
        sep = "," if "," in t else "."
        partes = t.split(sep)
        if len(partes) > 2:
            t = "".join(partes)
        elif len(partes[1]) == 3 and partes[0] not in ("", "0"):
            t = "".join(partes)
        else:
            t = partes[0] + "." + partes[1]

    try:
        valor = Decimal(t)
    except InvalidOperation:
        return None
    if not valor.is_finite() or valor.as_tuple().exponent < -2 or valor > VALOR_MAXIMO:
        return None
    return valor


CATEGORIA = {
    "OK": "ok",
    "SIN_SALDO": "aviso",
    "SALDO_INSUFICIENTE": "aviso",
    "NO_EXISTE": "error",
    "VALOR_INVALIDO": "error",
    "ID_INVALIDO": "error",
}


def texto_detalle(codigo, valor):
    if codigo == "OK":
        return f"Se pasaron {formato_moneda(valor)} del saldo al ahorro."
    return {
        "SIN_SALDO": "Su saldo está en $ 0, así que no se puede pasar nada al ahorro.",
        "SALDO_INSUFICIENTE": "Ingresa un valor menor o igual a su saldo.",
        "NO_EXISTE": "Toca una cuenta de la lista para usar su id.",
        "VALOR_INVALIDO": "Escribe solo números, por ejemplo 50000 o 50.000.",
        "ID_INVALIDO": "El id son solo números, por ejemplo 1001.",
    }.get(codigo, "")


def guardar_resultado(codigo, mensaje, id_cliente="", valor=None, saldo=None, ahorro=None):
    """Deja el resultado en la sesión para mostrarlo tras la redirección."""
    resultado = {
        "codigo": codigo,
        "categoria": CATEGORIA.get(codigo, "error"),
        "mensaje": mensaje,
        "detalle": texto_detalle(codigo, valor),
        "id": id_cliente,
        "saldo": None,
        "ahorro": None,
        "pct_ahorro": 0,
    }
    if saldo is not None and ahorro is not None:
        saldo, ahorro = Decimal(str(saldo)), Decimal(str(ahorro))
        total = saldo + ahorro
        resultado.update(
            saldo=str(saldo),
            ahorro=str(ahorro),
            pct_ahorro=round(float(ahorro / total * 100), 1) if total > 0 else 0,
        )
    session["resultado"] = resultado


@app.after_request
def sin_cache(respuesta):
    # Evita que el botón "Atrás" muestre saldos después de cerrar sesión.
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


# -------------------------------------------------------------------- rutas

@app.route("/")
def index():
    if not session.get("usuario"):
        return redirect(url_for("login"))

    resultado = session.pop("resultado", None)
    try:
        cuentas = servicios.listar_ahorros()
    except Exception:
        log.exception("Error listando las cuentas")
        cuentas = []
        flash("No se pudo consultar la base de datos. Intenta de nuevo.", "error")

    return render_template("index.html", cuentas=cuentas, resultado=resultado)


@app.route("/ahorrar", methods=["POST"])
def ahorrar():
    if not session.get("usuario"):
        return redirect(url_for("login"))

    texto_id = request.form.get("id_cliente", "").strip()
    texto_valor = request.form.get("valor", "")

    if not re.fullmatch(r"[0-9]{1,10}", texto_id) or int(texto_id) > ID_MAXIMO:
        guardar_resultado("ID_INVALIDO", "Ingresa el id del cliente.", texto_id)
        return redirect(url_for("index"))

    valor = parsear_valor(texto_valor)
    if valor is None or valor <= 0:
        guardar_resultado("VALOR_INVALIDO", "Ingresa un valor válido, mayor a cero.", texto_id)
        return redirect(url_for("index"))

    try:
        r = servicios.ahorrar(int(texto_id), valor)
    except Exception:
        log.exception("Error llamando al procedimiento ahorrar")
        flash("No se pudo completar la operación. Intenta de nuevo.", "error")
        return redirect(url_for("index"))

    guardar_resultado(
        r["o_codigo"],
        r["o_mensaje"],
        id_cliente="" if r["o_codigo"] == "OK" else texto_id,
        valor=valor,
        saldo=r["o_saldo"],
        ahorro=r["o_ahorro"],
    )
    return redirect(url_for("index"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        clave = request.form.get("clave", "")

        # compare_digest compara en tiempo constante (evita pistas por tiempo de respuesta)
        usuario_ok = hmac.compare_digest(usuario.encode(), USUARIO_APP.encode())
        clave_ok = hmac.compare_digest(clave.encode(), CLAVE_APP.encode())
        if usuario_ok and clave_ok:
            session.clear()
            session["usuario"] = USUARIO_APP
            return redirect(url_for("index"))

        flash("Usuario o contraseña incorrectos.", "error")
        return redirect(url_for("login"))

    if session.get("usuario"):
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Cerraste sesión.", "exito")
    return redirect(url_for("login"))


@app.errorhandler(404)
def no_encontrado(e):
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
