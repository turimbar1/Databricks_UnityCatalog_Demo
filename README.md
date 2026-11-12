# Flyway on Databricks Unity Catalog: demo project

A Flyway Enterprise project for demoing database DevOps on Databricks Unity Catalog. It covers schema-model capture, generated migrations and undo scripts, code review, drift detection and deployment, all against managed Delta tables.

## What's in the repo

| Path | What it is |
|---|---|
| `flyway.toml` | Project config. Environments `prod` (catalog `demo_prod`) and `Dev2` (`demo_dev`). Your `development` and `shadow` environments live in your own `flyway.user.toml`. |
| `schema-model/` | The schema model: 8 tables and 1 view in `default` |
| `migrations/` | `B001` baseline (tables plus seed data), `V002` orders and `recent_orders` (prod only, see its `.conf`), `V003` `category_type`, plus `U002` / `U003` undo scripts |
| `demo-samples/` | Ready-made dev changes to capture live in the demo (become V004). See [demo-samples/README.md](demo-samples/README.md). |
| `demo-drift/` | Hand-made prod changes, plus a script that puts them into `demo_prod` so the drift report has something to show. See [demo-drift/README.md](demo-drift/README.md). |
| `.github/workflows/prod-drift-reset.yml` | Nightly job that rebuilds `demo_prod` from `master` and puts the drift back |

## Environments

| Environment | Catalog | Role |
|---|---|---|
| `development` | `demo_dev` | Where changes are made by hand in the SQL editor, then captured in Flyway Desktop |
| `shadow` | `demo_shadow` | Flyway's scratch database for generating and validating migrations (rebuilt with `clean`) |
| `prod` | `demo_prod` | The deployment target. Has deliberate drift after each reset. You sign in through a browser; the GitHub Action swaps this to a token on its runner. |

## Seed data

`B001` creates the baseline tables and fills them with a small Northwind-style data set: 3 regions, categories, shippers, suppliers, employees and customers, plus 4 products. Child rows look up their parents by name (for example a product joins to its supplier on `supplier_name`). Databricks identity columns don't guarantee which row gets which ID, so hard-coded `1, 2, 3` foreign keys aren't safe.

`orders` is created in `V002`, so it has no seed rows yet, and `recent_orders` returns nothing.

> Editing `B001` changes its checksum. Any environment that already ran `B001` as a script needs `flyway repair -environment=<env>` before it will migrate again. Prod doesn't, because `demo-drift` rebuilds it.

## The demo process

```
 Dev (demo_dev)                 Flyway Desktop                        Prod (demo_prod)
 ─────────────                  ──────────────                        ────────────────
 1. Run demo-samples 01-03  ──► 2. Refresh schema model, save
                                3. Generate V004 + U004 (undo)
                                4. Code review (AM05 on recent_orders)
                                   run 04 → recapture → clean      ┌─ nightly / on-demand reset:
                                5. Drift check against prod  ◄─────┤  wipe → migrate B001..V003
                                   → 5 drift items found            │  + save snapshot → add drift
                                6. Deploy V004 (-saveSnapshot)  ──►└─ (demo-drift/prod_drift.py)
                                7. Show flyway_schema_history
```

1. **Make the change in dev.** In the Databricks SQL editor, run `demo-samples/01` → `02` → `03` against `demo_dev`.
2. **Capture it.** In Flyway Desktop, refresh the **Schema model** and save the pending changes (new columns, `product_batches` and its foreign keys, `expiring_batches`).
3. **Generate.** Flyway Desktop generates `V004__…` plus a matching `U004__…` undo script, and orders the foreign keys and the view correctly.
4. **Code review.** The existing `recent_orders` fails rule AM05 because it uses bare `JOIN`. Run `demo-samples/04`, capture it again, and the errors go away.
5. **Drift check.** Before deploying, run a drift check against **Prod Demo**. It finds five changes nobody put in a migration:

   | Drift | Story |
   |---|---|
   | `orders.priority_flag` added | Hotfix during an incident |
   | `recent_orders` widened to 14 days | Would be silently overwritten by `demo-samples/04` |
   | `orders_backup_inc4471` | Backup table left behind |
   | `products.unit_price` comment changed | Unity Catalog metadata drift |
   | `orders_shippers_fk` dropped | Missing object |

   Flyway also generates resolution scripts: one to bring the drift into a migration, one to revert it.
6. **Deploy.** `flyway migrate -environment=prod -saveSnapshot=true` (or **Migrate** in Desktop with `migrate.saveSnapshot=true`). Saving a snapshot gives the next drift check a fresh starting point.
7. **Audit.** Show `flyway_schema_history` in `demo_prod`: who deployed what, and when.

The command-line version of step 5, for the "the pipeline blocked a bad deploy" story:

```powershell
flyway check -drift -environment=prod -failOnDrift=true -generateDriftResolutionScripts=true
```

## Resetting prod between demos

Prod has to start each demo with the baseline plus the drift. You can reset it two ways.

**Automatically.** GitHub Actions → **prod-drift-reset** runs at 01:23 UTC on weekdays. Use **Run workflow** to reset before a call. The HTML drift report is attached to each run as `prod-drift-report`.

**From your machine:**

```powershell
pip install databricks-sdk
databricks auth login --host https://adb-7405611424302232.12.azuredatabricks.net
python demo-drift/prod_drift.py reset     # wipe demo_prod.default, migrate from this checkout, snapshot, add drift
python demo-drift/prod_drift.py check     # just regenerate demo-drift/reports/prod-drift.html
```

`reset` builds prod from the branch you have checked out, so use `master` unless you mean otherwise. It refuses to run against any catalog that doesn't start with `demo_`.

Afterwards, roll dev back with the generated `U004` undo script, or just drop the demo objects in `demo_dev`.

## One-time setup

**Each SE needs:**

- Flyway Desktop / CLI with an Enterprise licence
- Access to the workspace `adb-7405611424302232.12.azuredatabricks.net`, warehouse `353a9a5f7ad7299f`, and the `demo_dev`, `demo_shadow` and `demo_prod` catalogs
- A `flyway.user.toml` with their `development` and `shadow` environments. It's gitignored, so copy the shape from a colleague.

**For the nightly reset**, add these repo secrets (Settings → Secrets and variables → Actions):

| Secret | Value |
|---|---|
| `DATABRICKS_TOKEN` | A PAT, preferably for a service principal, that owns `demo_prod` and can use the warehouse |
| `FLYWAY_EMAIL` | Redgate account email with an Enterprise licence |
| `FLYWAY_TOKEN` | Redgate personal access token for that account |

## Branches

`master` is the clean demo. Personal branches (for example `Rene`, `reyes`) are for SEs' own variations. Prod resets always rebuild from `master`, so don't merge demo-time V004s back into it.

All SEs currently share `demo_prod`, so a reset affects everyone. To give each SE their own prod, add a `prod_<name>` environment pointing at a `demo_prod_<name>` catalog, and run `prod_drift.py --environment prod_<name>`.
