-- Simplified seed data that works with existing table structures
-- This version uses UUIDs that will work with your existing data

-- 1. Create or update default user
INSERT INTO users (id, email, role, created_at)
VALUES (
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'admin@cival.trading',
    'admin',
    NOW()
) ON CONFLICT (id) DO UPDATE SET
    email = EXCLUDED.email,
    role = EXCLUDED.role;

-- 2. Create or update default wallet (only if columns exist)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'wallets' AND column_name = 'id' AND table_schema = 'public'
    ) THEN
        INSERT INTO wallets (id, user_id, name, type, balance, currency, is_active)
        VALUES (
            'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
            'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
            'Main Trading Wallet',
            'spot',
            100000.00,
            'USDT',
            true
        ) ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            balance = EXCLUDED.balance;
    END IF;
END $$;

-- 3. Add supported currencies (if table exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'supported_currencies' AND table_schema = 'public'
    ) THEN
        INSERT INTO supported_currencies (symbol, name, decimals, is_active)
        VALUES 
            ('USDT', 'Tether', 6, true),
            ('USDC', 'USD Coin', 6, true),
            ('BTC', 'Bitcoin', 8, true),
            ('ETH', 'Ethereum', 18, true),
            ('BNB', 'Binance Coin', 8, true)
        ON CONFLICT (symbol) DO NOTHING;
    END IF;
END $$;

-- 4. Create default trading strategies (if table structure supports it)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trading_strategies' AND column_name = 'id' AND table_schema = 'public'
    ) THEN
        INSERT INTO trading_strategies (id, name, type, parameters, status)
        VALUES 
            ('c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Momentum Strategy', 'momentum', 
             '{"timeframe": "1h", "lookback": 20, "threshold": 0.02}', 'active'),
            ('c1eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Mean Reversion', 'mean_reversion',
             '{"timeframe": "4h", "sma_period": 50, "std_dev": 2}', 'active'),
            ('c2eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Arbitrage Bot', 'arbitrage',
             '{"min_spread": 0.001, "max_position": 10000}', 'inactive')
        ON CONFLICT (id) DO NOTHING;
    END IF;
END $$;

-- 5. Create autonomous agents (if table structure supports it)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'autonomous_agents' AND column_name = 'id' AND table_schema = 'public'
    ) THEN
        INSERT INTO autonomous_agents (
            id, name, type, status, configuration, capabilities, memory_bank,
            learning_rate, exploration_rate, created_at
        )
        VALUES 
            ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Alpha Trader', 'trading', 'active',
             '{"strategy_id": "c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11", "risk_limit": 0.02}',
             '["market_analysis", "order_execution", "risk_management"]',
             '{"learned_patterns": [], "performance_history": []}',
             0.001, 0.1, NOW()),
            ('d1eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Risk Monitor', 'risk_management', 'active',
             '{"max_drawdown": 0.1, "var_limit": 0.05}',
             '["risk_analysis", "portfolio_monitoring", "alert_generation"]',
             '{}', 0.001, 0.05, NOW()),
            ('d2eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Market Scanner', 'analysis', 'active',
             '{"scan_interval": 60, "symbols": ["BTC/USDT", "ETH/USDT"]}',
             '["market_scanning", "signal_generation", "trend_analysis"]',
             '{}', 0.001, 0.15, NOW())
        ON CONFLICT (id) DO NOTHING;
    END IF;
END $$;

-- 6. Create sample market data (if table exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'market_data' AND table_schema = 'public'
    ) THEN
        INSERT INTO market_data (symbol, price, volume, timestamp)
        VALUES 
            ('BTC/USDT', 45000.00, 1234567890.00, NOW() - INTERVAL '5 minutes'),
            ('BTC/USDT', 45100.00, 1234567900.00, NOW() - INTERVAL '4 minutes'),
            ('BTC/USDT', 45050.00, 1234567910.00, NOW() - INTERVAL '3 minutes'),
            ('BTC/USDT', 45150.00, 1234567920.00, NOW() - INTERVAL '2 minutes'),
            ('BTC/USDT', 45200.00, 1234567930.00, NOW() - INTERVAL '1 minute'),
            ('BTC/USDT', 45250.00, 1234567940.00, NOW()),
            ('ETH/USDT', 2400.00, 987654321.00, NOW() - INTERVAL '5 minutes'),
            ('ETH/USDT', 2410.00, 987654331.00, NOW() - INTERVAL '4 minutes'),
            ('ETH/USDT', 2405.00, 987654341.00, NOW() - INTERVAL '3 minutes'),
            ('ETH/USDT', 2415.00, 987654351.00, NOW() - INTERVAL '2 minutes'),
            ('ETH/USDT', 2420.00, 987654361.00, NOW() - INTERVAL '1 minute'),
            ('ETH/USDT', 2425.00, 987654371.00, NOW());
    END IF;
END $$;

-- 7. Create trading goals (if table exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'goals' AND table_schema = 'public'
    ) THEN
        INSERT INTO goals (
            id, user_id, title, description, type, status, 
            target_value, current_value, deadline
        )
        VALUES 
            ('g0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
             'Daily Profit Target', 'Achieve $5000 daily profit', 'profit', 'active',
             5000.00, 3250.00, NOW() + INTERVAL '1 day'),
            ('g1eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
             'Risk Management', 'Keep drawdown below 5%', 'risk', 'active',
             5.00, 2.30, NOW() + INTERVAL '30 days'),
            ('g2eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
             'Win Rate Improvement', 'Achieve 75% win rate', 'performance', 'active',
             75.00, 68.50, NOW() + INTERVAL '14 days')
        ON CONFLICT (id) DO NOTHING;
    END IF;
END $$;

-- 8. Create sample positions (if table exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'positions' AND table_schema = 'public'
    ) THEN
        INSERT INTO positions (
            id, user_id, symbol, side, quantity, entry_price, 
            current_price, unrealized_pnl, status
        )
        VALUES 
            ('p0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
             'BTC/USDT', 'long', 0.5, 44800.00, 45250.00, 225.00, 'open'),
            ('p1eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
             'ETH/USDT', 'long', 5.0, 2380.00, 2425.00, 225.00, 'open')
        ON CONFLICT (id) DO NOTHING;
    END IF;
END $$;

-- 9. Create sample alerts (using newly created table)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'alerts' AND table_schema = 'public'
    ) THEN
        INSERT INTO alerts (
            user_id, alert_type, severity, title, message, source
        )
        VALUES 
            ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'price', 'info',
             'BTC Price Alert', 'BTC/USDT reached $45,250', 'market_monitor'),
            ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'risk', 'warning',
             'Drawdown Warning', 'Portfolio drawdown approaching 3%', 'risk_monitor');
    END IF;
END $$;

-- 10. Add user preferences (if table exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'user_preferences' AND table_schema = 'public'
    ) THEN
        INSERT INTO user_preferences (user_id, preferences)
        VALUES (
            'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
            '{
                "theme": "dark",
                "notifications": {
                    "email": true,
                    "push": true,
                    "sms": false
                },
                "trading": {
                    "default_leverage": 1,
                    "risk_per_trade": 0.02,
                    "preferred_timeframe": "1h"
                },
                "display": {
                    "currency": "USD",
                    "timezone": "UTC",
                    "decimal_places": 2
                }
            }'::jsonb
        ) ON CONFLICT (user_id) DO NOTHING;
    END IF;
END $$;

-- Success message
SELECT 'Simplified seed data inserted successfully!' as status;