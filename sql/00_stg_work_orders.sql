-- Staging view: one clean row per work order.
-- Fixes the data-quality issues found in profiling and adds derived metrics
-- so every downstream query works from the same definitions.
DROP VIEW IF EXISTS stg_work_orders;
CREATE VIEW stg_work_orders AS
SELECT
    wo.work_order_id,
    wo.store_id,
    s.region,
    s.store_format,
    wo.vendor_id,
    v.vendor_name,
    v.trade,                                           -- vendor master is the trusted source (raw trade has casing issues)
    COALESCE(wo.problem_code, 'Unknown')    AS problem_code,
    wo.priority,
    wo.sla_hours,
    wo.status,
    wo.created_at,
    wo.assigned_at,
    wo.completed_at,
    strftime('%Y-%m', wo.created_at)        AS created_month,
    wo.nte_amount,
    wo.invoice_amount,
    wo.recall_of_work_order_id,
    ROUND((julianday(wo.completed_at) - julianday(wo.created_at)) * 24, 2) AS resolution_hours,
    CASE
        WHEN wo.status <> 'Completed' THEN NULL
        WHEN (julianday(wo.completed_at) - julianday(wo.created_at)) * 24 <= wo.sla_hours THEN 1
        ELSE 0
    END                                     AS sla_met,
    CASE WHEN wo.invoice_amount > wo.nte_amount THEN 1 ELSE 0 END AS over_nte
FROM work_orders wo
JOIN stores  s ON s.store_id  = wo.store_id
JOIN vendors v ON v.vendor_id = wo.vendor_id;
