# Banco de ahorros (Flask + Neon + Vercel)

Un cajero inicia sesión, escribe el **id del cliente** y un **valor**; el valor se
**resta del saldo** y se **suma al ahorro** del cliente.

## Base de datos
Una sola tabla, `ahorros(id, saldo, ahorro)`, y un procedimiento almacenado
`sp_ahorrar` que hace la operación de forma atómica. Ejecuta `schema.sql`
completo en el SQL Editor de Neon (se puede correr más de una vez sin problema).

El procedimiento responde con un código: `OK`, `NO_EXISTE`, `SIN_SALDO`
(saldo en cero), `VALOR_INVALIDO` o `SALDO_INSUFICIENTE`.

## Variables de entorno
| Variable | Descripción |
|---|---|
| `DATABASE_URL` | connection string de Neon (con `sslmode=require`) |
| `SECRET_KEY` | cadena aleatoria larga para firmar la sesión |
| `BANCO_USUARIO` | usuario del cajero para iniciar sesión |
| `BANCO_CLAVE` | contraseña del cajero |

Copia `.env.example` a `.env` para trabajar en local. En Vercel agrégalas en
*Settings → Environment Variables*.

## Local
    python -m venv .venv
    .venv\Scripts\activate           # Linux/Mac: source .venv/bin/activate
    pip install -r requirements.txt
    flask --app api.index run --debug

## Clientes de prueba (incluidos en schema.sql)
| id | saldo | ahorro | sirve para probar |
|---|---|---|---|
| 1001 | 500,000.00 | 0.00 | ahorro normal |
| 1002 | 0.00 | 120,000.00 | aviso de saldo en cero |
| 1003 | 75,000.50 | 25,000.00 | valores con decimales |

## Despliegue
Repositorio en GitHub conectado a Vercel (despliegue automático en cada push).
