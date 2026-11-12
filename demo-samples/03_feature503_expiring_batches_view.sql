-- Feature503: Released batches expiring in the next 90 days
-- Uses fully qualified joins (INNER JOIN / LEFT OUTER JOIN) so it passes code review rule AM05.
-- Run 02 first - this view depends on product_batches.
USE CATALOG demo_dev;

CREATE VIEW `default`.`expiring_batches` AS
SELECT b.batch_id, b.lot_number, p.product_name, p.ndc_code, s.supplier_name, b.expiry_date,
       datediff(b.expiry_date, current_date()) AS days_to_expiry
FROM product_batches b
INNER JOIN products p ON b.product_id = p.product_id
LEFT OUTER JOIN suppliers s ON b.supplier_id = s.supplier_id
WHERE b.release_status = 'RELEASED'
  AND b.expiry_date <= date_add(current_date(), 90);
