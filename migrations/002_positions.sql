-- 002_positions: ações que você possui, com quantidade e preço médio.
-- As ações monitoradas são as desta tabela.

CREATE TABLE positions (
    ticker     TEXT           PRIMARY KEY CHECK (ticker = upper(ticker)),
    quantity   INTEGER        NOT NULL CHECK (quantity > 0),
    avg_price  NUMERIC(12, 4) NOT NULL CHECK (avg_price > 0),
    updated_at TIMESTAMPTZ    NOT NULL DEFAULT now()
);
