-- Trades Table
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL,
    pair TEXT NOT NULL,
    direction TEXT NOT NULL, -- LONG, SHORT
    model TEXT,
    session TEXT,
    entry_price REAL,
    stop_loss REAL,
    target1 REAL,
    target2 REAL,
    position_size REAL,
    risk_dollars REAL,
    risk_percent REAL,
    confidence TEXT,
    status TEXT DEFAULT 'OPEN', -- OPEN, CLOSED, CANCELLED
    outcome TEXT, -- WIN, LOSS, BE
    realized_pnl REAL,
    r_achieved REAL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Confluences (Many-to-One with Trades)
CREATE TABLE IF NOT EXISTS trade_confluences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id INTEGER NOT NULL,
    confluence TEXT NOT NULL,
    FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE CASCADE
);

-- Mistakes (Many-to-One)
CREATE TABLE IF NOT EXISTS trade_mistakes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id INTEGER NOT NULL,
    mistake TEXT NOT NULL,
    FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE CASCADE
);

-- Lessons (Many-to-One)
CREATE TABLE IF NOT EXISTS trade_lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id INTEGER NOT NULL,
    lesson TEXT NOT NULL,
    FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE CASCADE
);

-- Journal Entries (General daily thoughts, linked to date)
CREATE TABLE IF NOT EXISTS journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    content TEXT NOT NULL,
    sentiment TEXT, -- BULLISH, BEARISH, NEUTRAL
    tags TEXT, -- JSON array or comma separated
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Core ICT Concepts
CREATE TABLE IF NOT EXISTS ict_concepts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    definition TEXT NOT NULL,
    category TEXT, -- 'Setup', 'Tool', 'Market Structure', 'Time'
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Models (Specific Trading Strategies)
CREATE TABLE IF NOT EXISTS trading_models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    entry_conditions TEXT, -- JSON or text list
    risk_reward TEXT,
    win_rate_target REAL,
    active BOOLEAN DEFAULT 1
);

-- User Memory (The "Coach")
CREATE TABLE IF NOT EXISTS user_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_key TEXT NOT NULL, -- e.g., "first_loss_best_loss"
    value TEXT NOT NULL,
    category TEXT, -- 'Psychology', 'Rule', 'Observation'
    source TEXT, -- 'Trade Review', 'ICT Core', etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User Patterns (Psychological Profiling)
CREATE TABLE IF NOT EXISTS user_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern TEXT NOT NULL, -- e.g., "Chases trades"
    type TEXT, -- 'WEAKNESS', 'STRENGTH'
    mitigation_strategy TEXT,
    last_detected TIMESTAMP
);
