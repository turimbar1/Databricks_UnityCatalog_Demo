-- Feature502: Batch / lot genealogy table with QA release tracking (GxP traceability story)
-- Managed Delta table in Unity Catalog with identity PK and informational FKs.
USE CATALOG demo_dev;

CREATE TABLE `default`.`product_batches` (
    `batch_id` bigint NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1),
    `product_id` bigint NOT NULL COMMENT 'Product this batch was manufactured for.',
    `supplier_id` bigint COMMENT 'Contract manufacturer or supplier that produced the batch.',
    `lot_number` string NOT NULL COMMENT 'Manufacturer lot number printed on the packaging.',
    `manufactured_date` date,
    `expiry_date` date,
    `release_status` string COMMENT 'QA release status: QUARANTINE, RELEASED or REJECTED.',
    `released_by` bigint COMMENT 'employee_id of the QA approver who released the batch.',
    `released_at` timestamp,
    CONSTRAINT `product_batches_pk` PRIMARY KEY (`batch_id`)
)
COMMENT 'Batch and lot genealogy with QA release status, supporting recall and audit traceability.';

ALTER TABLE `default`.`product_batches` ADD CONSTRAINT `product_batches_products_fk` FOREIGN KEY (`product_id`) REFERENCES `default`.`products` (`product_id`);

ALTER TABLE `default`.`product_batches` ADD CONSTRAINT `product_batches_suppliers_fk` FOREIGN KEY (`supplier_id`) REFERENCES `default`.`suppliers` (`supplier_id`);

ALTER TABLE `default`.`product_batches` ADD CONSTRAINT `product_batches_employees_fk` FOREIGN KEY (`released_by`) REFERENCES `default`.`employees` (`employee_id`);
