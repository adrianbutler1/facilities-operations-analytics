-- SLA compliance by priority and region (completed work orders only).
SELECT
    region,
    priority,
    COUNT(*)                                AS completed_wos,
    ROUND(100.0 * AVG(sla_met), 1)          AS sla_compliance_pct,
    ROUND(AVG(resolution_hours), 1)         AS avg_resolution_hours
FROM stg_work_orders
WHERE status = 'Completed'
GROUP BY region, priority
ORDER BY region, priority;
