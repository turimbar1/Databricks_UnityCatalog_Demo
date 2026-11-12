# Unity Catalog sample changes (demo)

These are sample changes built on the current schema model: 8 tables and 1 view in `default`, with the baseline plus V002 and V003 already applied. They live outside `migrations/` and `schema-model/`, so Flyway ignores them until you capture them.

| Script | Change | What it shows |
|---|---|---|
| 01 | Adds `ndc_code`, `storage_condition` and `is_controlled_substance` to `products`, plus a table comment | Column adds with comments, so Unity Catalog metadata is versioned too |
| 02 | New `product_batches` table (identity PK, 3 FKs to products, suppliers and employees) | New managed Delta table with constraints |
| 03 | New `expiring_batches` view | Dependency ordering: the view depends on 01 and 02 |
| 04 | Rewrites `recent_orders` with explicit `INNER JOIN` | Fixes the 3 AM05 code review errors in `report-code-review.sarif` |

## Demo flow

1. In the Databricks SQL editor, run 01 → 02 → 03 against `demo_dev`. Each script starts with `USE CATALOG demo_dev`.
2. In Flyway Desktop, go to **Schema model** and refresh. The new columns, table, FKs and view show as pending changes. Save them to the schema model.
3. Go to **Generate migrations**. Flyway builds `V004__...` plus a matching `U004__...` undo script, because `undoScripts = true`. Show that the FKs and view are ordered correctly.
4. Run code review. The new view passes. Then run 04, capture it, regenerate, and show the AM05 errors going away.
5. Before deploying, run a drift check against `prod`. It finds the hand-made changes from `demo-drift/` (see `demo-drift/README.md`).
6. Deploy to `prod` with `-saveSnapshot=true`, and show `flyway_schema_history`: who deployed what, and when.

## Notes

- Everything here is a managed Delta table. That matches what Flyway supports on Databricks today. External and non-Delta tables are not supported.
- Dropping or renaming a column on Delta needs column mapping, which is why the U003 undo rebuilds `categories`. The easiest way to roll dev back after the demo is the generated U004 undo script.
- I haven't run these against your workspace, so do a quick dry run on `demo_dev` first.
