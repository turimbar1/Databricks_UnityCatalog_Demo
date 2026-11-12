-- DRIFT 03: the classic "backup table" left behind after an incident.
-- Drift report: extra table default.orders_backup_inc4471.
USE CATALOG demo_prod;

CREATE TABLE `default`.`orders_backup_inc4471` AS SELECT * FROM `default`.`orders`;
