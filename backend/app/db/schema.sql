CREATE TABLE daily_bhavcopy (
    id SERIAL PRIMARY KEY,
    trade_date DATE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    expiry_date DATE NOT NULL,
    open NUMERIC(12,2),
    high NUMERIC(12,2),
    low NUMERIC(12,2),
    close NUMERIC(12,2),
    volume BIGINT DEFAULT 0,
    open_interest BIGINT DEFAULT 0,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(trade_date, symbol, expiry_date)
);

CREATE TABLE normalized_prices (
    id SERIAL PRIMARY KEY,
    trade_date DATE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    expiry_date DATE NOT NULL,
    raw_close NUMERIC(12,2) NOT NULL,
    norm_close_10g_999 NUMERIC(14,4) NOT NULL,
    purity_multiplier NUMERIC(10,6) NOT NULL,
    unit_multiplier NUMERIC(10,6) NOT NULL,
    volume BIGINT DEFAULT 0,
    open_interest BIGINT DEFAULT 0,
    UNIQUE(trade_date, symbol, expiry_date)
);

CREATE INDEX idx_daily_bhavcopy_sym_exp_date ON daily_bhavcopy (symbol, expiry_date, trade_date);
CREATE INDEX idx_normalized_prices_sym_exp_date ON normalized_prices (symbol, expiry_date, trade_date);
