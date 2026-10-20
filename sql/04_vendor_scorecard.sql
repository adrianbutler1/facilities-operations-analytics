-- Vendor scorecard: speed, cost, and fix quality side by side.
-- Recall rate = share of a vendor's completed jobs that needed a callback
-- (a later work order linked via recall_of_work_order_id) because the fix didn't hold.
WITH recalls AS (
    SELECT recall_of_work_order_id AS work_order_id, COUNT(*) AS recall_count
    FROM stg_work_orders
    WHERE recall_of_work_order_id IS NOT NULL
    GROUP BY recall_of_work_order_id
),
vendor_stats AS (
    SELECT
        w.vendor_id,
        w.vendor_name,
        w.trade,
        COUNT(*)                                            AS completed_wos,
        ROUND(100.0 * AVG(w.sla_met), 1)                    AS sla_compliance_pct,
        ROUND(AVG(w.resolution_hours), 1)                   AS avg_resolution_hours,
        ROUND(AVG(w.invoice_amount), 0)                     AS avg_invoice,
        ROUND(100.0 * AVG(w.over_nte), 1)                   AS pct_over_nte,
        ROUND(100.0 * AVG(r.recall_count IS NOT NULL), 1)   AS recall_pct
    FROM stg_work_orders w
    LEFT JOIN recalls r ON r.work_order_id = w.work_order_id
    WHERE w.status = 'Completed'
      AND w.recall_of_work_order_id IS NULL      -- score vendors on original jobs only
    GROUP BY w.vendor_id, w.vendor_name, w.trade
)
SELECT
    *,
    RANK() OVER (PARTITION BY trade ORDER BY sla_compliance_pct DESC) AS sla_rank_in_trade,
    RANK() OVER (PARTITION BY trade ORDER BY recall_pct ASC)          AS quality_rank_in_trade
FROM vendor_stats
ORDER BY trade, recall_pct;
