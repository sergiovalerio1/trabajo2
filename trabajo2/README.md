# Sistema de clientes (Flask + Neon + Vercel)

Registro, inicio de sesión y consulta de saldo/abonos de clientes.

## Variables de entorno
- `DATABASE_URL`: connection string de Neon (con `sslmode=require`)
- `SECRET_KEY`: cadena aleatoria larga para firmar la sesión

## Local
    python -m venv .venv
    source .venv/bin/activate        # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    flask --app api.index run --debug

## Base de datos
Ejecutar `schema.sql` en el SQL Editor de Neon.

## Despliegue
Repositorio en GitHub conectado a Vercel (despliegue automático en cada push).