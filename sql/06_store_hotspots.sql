-- Stores with the most work orders per 10k sq ft, plus spend.
SELECT
    w.store_id,
    w.region,
    w.store_format,
    s.open_year,
    COUNT(*)                                            AS work_orders,
    ROUND(COUNT(*) * 10000.0 / s.sq_ft, 1)              AS wos_per_10k_sqft,
    ROUND(SUM(w.invoice_amount), 0)                     AS total_spend
FROM stg_work_orders w
JOIN stores s ON s.store_id = w.store_id
GROUP BY w.store_id, w.region, w.store_format, s.open_year, s.sq_ft
ORDER BY wos_per_10k_sqft DESC;
