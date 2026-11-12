-- DRIFT 04: Unity Catalog metadata changed by hand. Column comments are part of the schema model,
-- so a changed comment is drift too.
-- Drift report: default.products changed, unit_price comment differs.
USE CATALOG demo_prod;

ALTER TABLE `default`.`products` ALTER COLUMN `unit_price` COMMENT 'Selling price per unit in GBP. Changed directly in prod by finance, Nov 2026.';
