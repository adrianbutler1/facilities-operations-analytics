-- Open backlog aging as of the snapshot date, by trade.
-- :as_of is passed in as a parameter.
SELECT
    trade,
    CASE
        WHEN julianday(:as_of) - julianday(created_at) <= 7  THEN '1) 0-7 days'
        WHEN julianday(:as_of) - julianday(created_at) <= 30 THEN '2) 8-30 days'
        WHEN julianday(:as_of) - julianday(created_at) <= 90 THEN '3) 31-90 days'
        ELSE '4) 90+ days'
    END      AS age_bucket,
    COUNT(*) AS open_wos
FROM stg_work_orders
WHERE status IN ('Open', 'In Progress')
GROUP BY trade, age_bucket
ORDER BY trade, age_bucket;
