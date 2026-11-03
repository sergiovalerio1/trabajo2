-- =====================================================================
--  BANCO  ·  base de datos (PostgreSQL / Neon)
--  Una sola tabla: ahorros(id, saldo, ahorro)
--  Ejecutar completo en el SQL Editor de Neon.
-- =====================================================================

-- 1) Limpieza del sistema anterior (registro/login de clientes)
DROP FUNCTION IF EXISTS registrar_usuario(varchar, varchar, varchar);
DROP FUNCTION IF EXISTS obtener_usuario(varchar);
-- Si la tabla anterior tenía otro nombre (p. ej. "clientes"), bórrala aquí:
-- DROP TABLE IF EXISTS clientes CASCADE;

-- 2) Tabla única
CREATE TABLE IF NOT EXISTS ahorros (
    id      VARCHAR(20)   PRIMARY KEY,
    saldo   NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (saldo  >= 0),
    ahorro  NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (ahorro >= 0)
);

-- 3) Procedimiento almacenado: resta del saldo y suma al ahorro.
--    Devuelve (p_codigo, p_saldo, p_ahorro). Códigos posibles:
--      OK · NO_EXISTE · SIN_SALDO · VALOR_INVALIDO · SALDO_INSUFICIENTE
CREATE OR REPLACE PROCEDURE sp_ahorrar(
    p_id      VARCHAR,
    p_valor   NUMERIC,
    INOUT p_codigo TEXT    DEFAULT NULL,
    INOUT p_saldo  NUMERIC DEFAULT NULL,
    INOUT p_ahorro NUMERIC DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Bloquea la fila para que dos operaciones simultáneas no se pisen
    SELECT a.saldo, a.ahorro
      INTO p_saldo, p_ahorro
      FROM ahorros a
     WHERE a.id = p_id
       FOR UPDATE;

    IF NOT FOUND THEN
        p_codigo := 'NO_EXISTE';
        RETURN;
    END IF;

    IF COALESCE(p_saldo, 0) <= 0 THEN
        p_codigo := 'SIN_SALDO';          -- sin saldo o en cero
        RETURN;
    END IF;

    IF p_valor IS NULL OR p_valor <= 0 THEN
        p_codigo := 'VALOR_INVALIDO';
        RETURN;
    END IF;

    IF p_valor > p_saldo THEN
        p_codigo := 'SALDO_INSUFICIENTE';
        RETURN;
    END IF;

    UPDATE ahorros
       SET saldo  = saldo  - p_valor,
           ahorro = ahorro + p_valor
     WHERE id = p_id
    RETURNING saldo, ahorro INTO p_saldo, p_ahorro;

    p_codigo := 'OK';
END;
$$;

-- 4) Clientes de prueba (puedes borrarlos o cambiarlos)
INSERT INTO ahorros (id, saldo, ahorro) VALUES
    ('1001', 500000.00,      0.00),   -- saldo normal
    ('1002',      0.00, 120000.00),   -- saldo en cero (prueba del aviso)
    ('1003',  75000.50,  25000.00)
ON CONFLICT (id) DO NOTHING;
