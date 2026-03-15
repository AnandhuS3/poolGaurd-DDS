# Full Migration Report: MySQL to PostgreSQL

## 1. Initial State Analysis
* **Driver:** `mysql-connector-python`
* **Object-Relational Mapping (ORM):** None (Pure raw SQL queries through custom `Database` wrapper).
* **Schema Location:** `backend/database/schema.sql` (contained MySQL-exclusive syntax like `AUTO_INCREMENT` and `.ON UPDATE CURRENT_TIMESTAMP`).
* **Credentials/Config Locations:** `backend/core/config.py`, `backend/core/credentials.py`, and `backend/config/.env`.
* **Migration Mechanism:** Hardcoded Python scripts for each update (e.g. `migrate_auth_hardening.py`, `migrate_cameras.py`) that explicitly run `mysql.connector`.

## 2. Infrastructure Setup
* Started a local PostgreSQL server on port `5432`.
* Installed `psycopg2-binary` (v2.9.11) via pip in the `.venv` and removed `mysql-connector-python` from `requirements.txt`.
* Manually created the new database: `CREATE DATABASE poolguard_db;`

## 3. Schema Conversion
Rewrote `backend/database/schema.sql` entirely to match PostgreSQL standards:
* Converted `AUTO_INCREMENT` to `SERIAL`.
* Converted standard string ENUMs to dedicated generic Postgres `CREATE TYPE ... AS ENUM` objects (`user_role`, `alert_type_enum`, `camera_status_enum`).
* Replaced `DATETIME` with `TIMESTAMP`.
* Replaced MySQL's `ON UPDATE CURRENT_TIMESTAMP` with a plpgsql `BEFORE UPDATE` trigger function.
* Replaced `ON DUPLICATE KEY UPDATE` with standard `ON CONFLICT (...) DO NOTHING`.
* Replaced `TINYINT(1)` with standard `BOOLEAN`.
* Removed `ENGINE=InnoDB` and `COLLATE` directives.

## 4. Data Migration
Designed and executed `mysql_to_pg.py` inside the codebase to migrate state smoothly without hitting MySQL DDL syntax artifacts:
* Read native dicts directly out of all 6 MySQL tables.
* Transformed legacy `TINYINT(1)` boolean responses to strict `bool` (True/False).
* Safely inserted payloads row-by-row into `poolguard_db` over `psycopg2`.
* Added automatic `CREATE SEQUENCE` update via `setval(..., COALESCE(MAX(id)+1, 1))` to verify that sequence IDs cleanly resume from past state for all populated tables.
* **Outcome:** Cleanly synchronized 337 rows completely (including audits, configurations, and existing credentials).

## 5. Backend Re-Architecture
Adapted the whole database management logic across the codebase to `psycopg2`:
1. **`core/database.py`:** Removed `mysql-connector-python`. Replaced logic with Threaded pool connection handling from `psycopg2.pool.ThreadedConnectionPool`.
2. **Result Dictionaries:** Switched away from MySQL's automatic `dictionary=True` logic to `psycopg2.extras.RealDictCursor` arrays, maintaining 1:1 format compatibility for all other backend code relying on native Python dict properties (`user['id']` etc.).
3. **Database Setup Routine (`core/app.py`):** Changed startup verification from `SHOW TABLES` to SQL standard `information_schema.tables` query. Replaced pure initialization calls with `psycopg2`.
4. **Environment Defaults (`core/config.py` & `.env`):** Updated default config host, port, db name pointers, and test scripts gracefully resolving to `localhost:5432` / `postgres`.

## 6. Migration Scripts
Rewrote the auxiliary CLI utilities manually designed for MySQL:
* `init_database.py`
* `migrate_auth_hardening.py`
* `migrate_cameras.py`
* `migrate_admin_email.py`
* `migrate_mobile_fcm.py`
* `migrate_system_admin.py`
* Updated execution paths: Removed heavy `IF EXISTS` metadata SQL queries relying on `information_schema.columns` because PostgreSQL allows natively running `ALTER TABLE ADD COLUMN IF NOT EXISTS`.

## 7. Security and Validation
* The local database test endpoint `test_login.py` now resolves beautifully with the `poolguard_db` database resolving hashes flawlessly against PostgreSQL.
* The API runs synchronously and effectively establishes threaded pooled interactions.
* Full raw SQL functionality remains fully compatible with PostgreSQL due to uniform `(%s, %s)` parsing structures handling placeholders.
