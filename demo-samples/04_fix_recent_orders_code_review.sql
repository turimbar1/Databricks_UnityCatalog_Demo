-- Fix: the existing recent_orders view fails code review rule AM05 (3 hits in report-code-review.sarif)
-- because it uses bare JOIN. This makes every join explicit so the next code review run is clean.
USE CATALOG demo_dev;

CREATE OR REPLACE VIEW `default`.`recent_orders` AS
SELECT o.order_id, o.order_date, c.customer_name, e.first_name, e.last_name, s.shipper_name
FROM orders o
INNER JOIN customers c ON o.customer_id = c.customer_id
INNER JOIN employees e ON o.employee_id = e.employee_id
INNER JOIN shippers s ON o.shipper_id = s.shipper_id
WHERE o.order_date >= DATEADD(day, -7, CURRENT_DATE);
