# Banco Sergio Valerio (Flask + Neon + Vercel)

App de ahorros pensada para el celular. Después de iniciar sesión pide el **id del cliente** y un **valor**;
un **procedimiento almacenado** resta ese valor al saldo y lo suma al ahorro. Avisa si el cliente no tiene
saldo (o está en cero), si el valor supera el saldo, si el id no existe y permite cerrar sesión.

## Base de datos
Una sola tabla: `ahorros (id, saldo, ahorro)`, con 5 clientes de prueba (el 1005 tiene saldo en cero).

1. Abre el **SQL Editor** de Neon.
2. Pega todo `schema.sql` y ejecútalo una vez.
   - Elimina las tablas y funciones de la versión anterior (usuarios, clave, abonos) para que quede solo `ahorros`.
   - Crea el procedimiento `ahorrar(id, valor, ...)` y la función `listar_ahorros()`.
   - Se puede volver a ejecutar sin reiniciar los saldos.

## Variables de entorno
| Variable | Para qué |
|---|---|
| `DATABASE_URL` | connection string de Neon (con `sslmode=require`) |
| `SECRET_KEY` | cadena aleatoria larga para firmar la sesión |
| `APP_USUARIO` | usuario para entrar a la app (opcional, por defecto `sergio`) |
| `APP_CLAVE` | contraseña para entrar a la app (opcional, por defecto `banco2026`) |

Para que la contraseña no sea la de demostración, agrega `APP_USUARIO` y `APP_CLAVE` en Vercel
(Settings > Environment Variables) y en tu `.env` local.

## Local
    python -m venv .venv
    .venv\Scripts\activate            # Linux/Mac: source .venv/bin/activate
    pip install -r requirements.txt
    flask --app api.index run --debug

## Despliegue
Repositorio en GitHub conectado a Vercel: cada `git push` a `main` despliega automáticamente.

## Estructura
- `api/index.py`: rutas (login, ahorrar, logout) y validación de lo que escribe la persona.
- `servicios.py`: llama al procedimiento y a la función de la base de datos (sin lógica de negocio).
- `schema.sql`: tabla, procedimiento, función y datos de prueba.
- `templates/`: `base.html` (estilos), `login.html`, `index.html`, `_logo.html`.
- `logo/`: logo Sergio Valerio (horizontal, versión blanca e ícono) en SVG y PNG.
