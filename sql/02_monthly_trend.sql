-- Monthly work-order volume by trade (seasonality).
SELECT
    created_month,
    trade,
    COUNT(*) AS work_orders
FROM stg_work_orders
GROUP BY created_month, trade
ORDER BY created_month, trade;
