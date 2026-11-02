-- 001_init: tabelas iniciais do alerta-investimentos.

-- Cada cotação recebida da brapi.
CREATE TABLE quotes (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticker      TEXT          NOT NULL,
    price       NUMERIC(12, 4) NOT NULL,
    change_pct  NUMERIC(8, 4)  NOT NULL,
    prev_close  NUMERIC(12, 4) NOT NULL,
    market_time TIMESTAMPTZ    NOT NULL,
    fetched_at  TIMESTAMPTZ    NOT NULL DEFAULT now(),
    UNIQUE (ticker, market_time)
);

-- Alertas já enviados: é o "anti-spam".
CREATE TABLE alerts (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticker      TEXT          NOT NULL,
    trade_date  DATE          NOT NULL,
    direction   TEXT          NOT NULL CHECK (direction IN ('up', 'down')),
    level       SMALLINT      NOT NULL CHECK (level > 0),
    change_pct  NUMERIC(8, 4)  NOT NULL,
    price       NUMERIC(12, 4) NOT NULL,
    sent_at     TIMESTAMPTZ    NOT NULL DEFAULT now(),

    UNIQUE (ticker, trade_date, direction, level)
);
