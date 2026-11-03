import os

import psycopg
from psycopg.rows import dict_row


class CServicios:
    """Acceso a datos: abre y cierra una conexión en cada llamada
    (Vercel es serverless, no hay procesos persistentes)."""

    def _conectar(self):
        dsn = os.environ.get("DATABASE_URL")
        if not dsn:
            raise RuntimeError("La variable de entorno DATABASE_URL no está definida.")
        # prepare_threshold=None: compatible con el pooler (PgBouncer) de Neon
        return psycopg.connect(dsn, row_factory=dict_row, prepare_threshold=None)

    def ahorrar(self, id_cliente, valor):
        """Llama al procedimiento almacenado sp_ahorrar.

        Devuelve un dict con:
          codigo -> OK | NO_EXISTE | SIN_SALDO | VALOR_INVALIDO | SALDO_INSUFICIENTE
          saldo, ahorro -> valores actuales del cliente (None si no existe)
        """
        # 'with' hace commit al salir sin error y cierra la conexión
        with self._conectar() as conn:
            fila = conn.execute(
                "CALL sp_ahorrar(%s::varchar, %s::numeric)", (id_cliente, valor)
            ).fetchone()
        return {
            "codigo": fila["p_codigo"],
            "saldo": fila["p_saldo"],
            "ahorro": fila["p_ahorro"],
        }
