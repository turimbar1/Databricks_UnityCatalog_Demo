-- Feature501: Product traceability columns (lot tracking, expiry, controlled-substance flag)
-- Run in the Databricks SQL editor against the DEV catalog, then capture in Flyway Desktop.
-- Guard: never run this against demo_prod - Flyway deploys there.
USE CATALOG demo_dev;

ALTER TABLE `default`.`products` ADD COLUMNS (
    `ndc_code` string COMMENT 'National Drug Code assigned to the product, used for regulatory reporting and traceability.',
    `storage_condition` string COMMENT 'Required storage condition for the product, e.g. 2-8C refrigerated or room temperature.',
    `is_controlled_substance` boolean COMMENT 'True when the product is a controlled substance and needs additional handling and audit controls.'
);

COMMENT ON TABLE `default`.`products` IS 'Product master. Source of truth for sellable items, linked to suppliers and categories.';
