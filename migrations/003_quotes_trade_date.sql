-- 003: market_time da brapi é o horário de atualização do dado, não do pregão.
-- Passamos a guardar a data do pregão e deduplicar por (ticker, pregão, preço).

ALTER TABLE quotes ADD COLUMN trade_date DATE NOT NULL;

ALTER TABLE quotes DROP CONSTRAINT quotes_ticker_market_time_key;
ALTER TABLE quotes ADD CONSTRAINT quotes_ticker_trade_date_price_key
    UNIQUE (ticker, trade_date, price);
