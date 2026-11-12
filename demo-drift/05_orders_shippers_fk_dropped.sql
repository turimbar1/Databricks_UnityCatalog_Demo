-- DRIFT 05: a foreign key dropped in prod so a bulk load of bad data would go through.
-- Drift report: default.orders is missing orders_shippers_fk.
-- Delete this file if you don't want the "missing object" case.
USE CATALOG demo_prod;

ALTER TABLE `default`.`orders` DROP CONSTRAINT `orders_shippers_fk`;
