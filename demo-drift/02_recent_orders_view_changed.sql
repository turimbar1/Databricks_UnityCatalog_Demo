-- DRIFT 02: someone widened the recent_orders view from 7 to 14 days in prod and added shipped_date.
-- Drift report: default.recent_orders definition differs.
-- Demo hook: demo-samples/04 rewrites this view, so deploying it without a drift check would silently
-- overwrite this prod hotfix.
USE CATALOG demo_prod;

CREATE OR REPLACE VIEW `default`.`recent_orders` AS
SELECT o.order_id, o.order_date, o.shipped_date, c.customer_name, e.first_name, e.last_name, s.shipper_name
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN employees e ON o.employee_id = e.employee_id
JOIN shippers s ON o.shipper_id = s.shipper_id
WHERE o.order_date >= DATEADD(day, -14, CURRENT_DATE);
