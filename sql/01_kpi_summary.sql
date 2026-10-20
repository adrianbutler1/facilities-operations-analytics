-- Headline KPIs for the full period.
SELECT
    COUNT(*)                                                    AS total_work_orders,
    SUM(status = 'Completed')                                   AS completed,
    ROUND(100.0 * AVG(sla_met), 1)                              AS sla_compliance_pct,
    ROUND(SUM(invoice_amount), 0)                               AS total_spend,
    ROUND(AVG(invoice_amount), 0)                               AS avg_cost_per_wo,
    ROUND(100.0 * SUM(over_nte) / SUM(status = 'Completed'), 1) AS pct_invoices_over_nte,
    SUM(status IN ('Open', 'In Progress'))                      AS open_backlog
FROM stg_work_orders;
