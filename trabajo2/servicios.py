import os

import psycopg
from psycopg.rows import dict_row


class CServicios:
    """Acceso a datos: abre y cierra una conexión en cada llamada
    (Vercel es serverless, no hay procesos persistentes).

    Aquí no hay lógica de negocio: todo vive en la base de datos
    (procedimiento ahorrar y función listar_ahorros, ver schema.sql)."""

    def _conectar(self):
        dsn = os.environ.get("DATABASE_URL")
        if not dsn:
            raise RuntimeError("La variable de entorno DATABASE_URL no está definida.")
        # prepare_threshold=None: compatible con el pooler (PgBouncer) de Neon
        return psycopg.connect(dsn, row_factory=dict_row, prepare_threshold=None)

    def ahorrar(self, id_cliente, valor):
        """Llama al procedimiento ahorrar(). Resta 'valor' al saldo y lo suma al ahorro.

        Devuelve un dict con: o_codigo, o_mensaje, o_saldo, o_ahorro.
        o_codigo es OK, SIN_SALDO, SALDO_INSUFICIENTE, NO_EXISTE o VALOR_INVALIDO.
        """
        # 'with' hace commit al salir sin error y cierra la conexión.
        # Los NULL son los parámetros INOUT: el procedimiento los llena y los devuelve.
        with self._conectar() as conn:
            return conn.execute(
                "CALL ahorrar(%s::integer, %s::numeric, "
                "NULL::text, NULL::text, NULL::numeric, NULL::numeric)",
                (id_cliente, valor),
            ).fetchone()

    def listar_ahorros(self):
        """Lista de dicts con id, saldo y ahorro de todos los clientes."""
        with self._conectar() as conn:
            return conn.execute(
                "SELECT id, saldo, ahorro FROM listar_ahorros()"
            ).fetchall()
