-- DRIFT 01: column added straight to prod during an incident (INC-4471), never captured in a migration.
-- Drift report: default.orders changed, extra column priority_flag.
USE CATALOG demo_prod;

ALTER TABLE `default`.`orders` ADD COLUMN (`priority_flag` boolean COMMENT 'Hotfix INC-4471: expedite flag for delayed shipments');
