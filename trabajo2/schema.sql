/* =====================================================================
   Banco Sergio Valerio - base de datos (PostgreSQL / Neon)

   Cómo usarlo: abre el SQL Editor de Neon, pega TODO este archivo y
   ejecútalo una sola vez. Se puede volver a ejecutar sin problema:
   no borra los datos de ahorros ni reinicia los saldos.

   La base queda con UNA sola tabla: ahorros (id, saldo, ahorro).
   La lógica vive en el procedimiento ahorrar() y en la función
   listar_ahorros(); Flask solo los llama.
   ===================================================================== */


/* ---------------------------------------------------------------------
   1. Limpieza de la versión anterior (usuarios, clave, abonos)
      Elimina las funciones viejas y cualquier tabla del esquema public
      que no sea "ahorros", para que la base quede con una sola tabla.
      Neon muestra en los mensajes cuáles tablas eliminó.
   --------------------------------------------------------------------- */
DROP FUNCTION IF EXISTS registrar_usuario(varchar, varchar, varchar);
DROP FUNCTION IF EXISTS obtener_usuario(varchar);

DO $$
DECLARE
    t RECORD;
BEGIN
    FOR t IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public' AND tablename <> 'ahorros'
    LOOP
        RAISE NOTICE 'Eliminando tabla anterior: %', t.tablename;
        EXECUTE format('DROP TABLE IF EXISTS public.%I CASCADE', t.tablename);
    END LOOP;
END
$$;


/* ---------------------------------------------------------------------
   2. Tabla única: ahorros
      id      llave primaria (número del cliente)
      saldo   dinero disponible del cliente
      ahorro  dinero que el cliente ya pasó a ahorro
      Los CHECK impiden saldos o ahorros negativos aunque alguien
      modifique la tabla directamente.
   --------------------------------------------------------------------- */
CREATE TABLE IF NOT EXISTS ahorros (
    id     INTEGER       PRIMARY KEY,
    saldo  NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (saldo  >= 0),
    ahorro NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (ahorro >= 0)
);


/* ---------------------------------------------------------------------
   3. Clientes de prueba (5). El 1005 tiene saldo en cero a propósito,
      para mostrar el aviso de "sin saldo".
      ON CONFLICT: si ya existen, no se tocan.
   --------------------------------------------------------------------- */
INSERT INTO ahorros (id, saldo, ahorro) VALUES
    (1001, 1500000, 250000),
    (1002,  800000,      0),
    (1003, 2300000, 600000),
    (1004,   50000,  10000),
    (1005,       0, 120000)
ON CONFLICT (id) DO NOTHING;


/* ---------------------------------------------------------------------
   4. Procedimiento almacenado: ahorrar
      Resta p_valor al saldo del cliente y se lo suma al ahorro.
      Devuelve (INOUT):
        o_codigo  OK | SIN_SALDO | SALDO_INSUFICIENTE | NO_EXISTE | VALOR_INVALIDO
        o_mensaje texto para mostrar al usuario
        o_saldo   saldo del cliente después de la operación
        o_ahorro  ahorro del cliente después de la operación
      FOR UPDATE bloquea la fila mientras se calcula, así dos operaciones
      al mismo tiempo sobre el mismo cliente no se pisan.
   --------------------------------------------------------------------- */
CREATE OR REPLACE PROCEDURE ahorrar(
    IN    p_id        INTEGER,
    IN    p_valor     NUMERIC,
    INOUT o_codigo    TEXT    DEFAULT NULL,
    INOUT o_mensaje   TEXT    DEFAULT NULL,
    INOUT o_saldo     NUMERIC DEFAULT NULL,
    INOUT o_ahorro    NUMERIC DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_saldo  NUMERIC;
    v_ahorro NUMERIC;
BEGIN
    IF p_id IS NULL OR p_valor IS NULL OR p_valor <= 0 THEN
        o_codigo  := 'VALOR_INVALIDO';
        o_mensaje := 'El valor debe ser mayor a cero.';
        RETURN;
    END IF;

    SELECT saldo, ahorro
      INTO v_saldo, v_ahorro
      FROM ahorros
     WHERE id = p_id
       FOR UPDATE;

    IF NOT FOUND THEN
        o_codigo  := 'NO_EXISTE';
        o_mensaje := format('No existe un cliente con el id %s.', p_id);
        RETURN;
    END IF;

    o_saldo  := v_saldo;
    o_ahorro := v_ahorro;

    IF v_saldo = 0 THEN
        o_codigo  := 'SIN_SALDO';
        o_mensaje := format('El cliente %s no tiene saldo disponible.', p_id);
        RETURN;
    END IF;

    IF p_valor > v_saldo THEN
        o_codigo  := 'SALDO_INSUFICIENTE';
        o_mensaje := format('El valor supera el saldo disponible del cliente %s.', p_id);
        RETURN;
    END IF;

    UPDATE ahorros
       SET saldo  = saldo  - p_valor,
           ahorro = ahorro + p_valor
     WHERE id = p_id
    RETURNING saldo, ahorro INTO o_saldo, o_ahorro;

    o_codigo  := 'OK';
    o_mensaje := format('Ahorro realizado para el cliente %s.', p_id);
END
$$;


/* ---------------------------------------------------------------------
   5. Función: listar_ahorros
      Devuelve todas las cuentas ordenadas por id.
   --------------------------------------------------------------------- */
CREATE OR REPLACE FUNCTION listar_ahorros()
RETURNS TABLE (id INTEGER, saldo NUMERIC, ahorro NUMERIC)
LANGUAGE sql
STABLE
AS $$
    SELECT a.id, a.saldo, a.ahorro FROM ahorros a ORDER BY a.id;
$$;


/* ---------------------------------------------------------------------
   Verificación rápida (opcional, ejecútala por separado):
     SELECT * FROM listar_ahorros();
     CALL ahorrar(1001, 50000, NULL, NULL, NULL, NULL);
     SELECT table_name FROM information_schema.tables
      WHERE table_schema = 'public';      -- debe mostrar solo: ahorros
   --------------------------------------------------------------------- */
