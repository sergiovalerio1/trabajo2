import os

import psycopg
from psycopg.rows import dict_row
from werkzeug.security import check_password_hash, generate_password_hash


class CServicios:
    """Acceso a datos: abre y cierra una conexión en cada llamada
    (Vercel es serverless, no hay procesos persistentes)."""

    def _conectar(self):
        dsn = os.environ.get("DATABASE_URL")
        if not dsn:
            raise RuntimeError("La variable de entorno DATABASE_URL no está definida.")
        # prepare_threshold=None: compatible con el pooler (PgBouncer) de Neon
        return psycopg.connect(dsn, row_factory=dict_row, prepare_threshold=None)

    def registrar_usuario(self, cedula, nombre, clave):
        """Devuelve (ok: bool, mensaje: str)."""
        clave_hash = generate_password_hash(clave)
        try:
            # 'with' hace commit al salir sin error y cierra la conexión
            with self._conectar() as conn:
                conn.execute(
                    
                    "SELECT registrar_usuario(%s::varchar, %s::varchar, %s::varchar)",
                    (cedula, nombre, clave_hash),
                )
            return True, "Usuario registrado correctamente. Ya puedes iniciar sesión."
        except psycopg.errors.UniqueViolation:
            return False, "Esa cédula ya está registrada."

    def consultar_usuario(self, cedula):
        """Devuelve el usuario (dict, incluye 'clave') o None."""
        with self._conectar() as conn:
            return conn.execute(

                "SELECT * FROM obtener_usuario(%s::varchar)", (cedula,)
            ).fetchone()

    def iniciar_sesion(self, cedula, clave):
        """Verifica el hash. Devuelve el usuario SIN la clave, o None."""
        usuario = self.consultar_usuario(cedula)
        if usuario is None or not check_password_hash(usuario["clave"], clave):
            return None
        usuario.pop("clave")
        return usuario