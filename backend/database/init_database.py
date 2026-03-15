"""
Database Initialization Script (PostgreSQL)
Run this script to set up the PostgreSQL database and create the initial admin user.
"""
import psycopg2
from psycopg2 import Error
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read_sql_file(filename):
    """Read SQL file and return contents"""
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()


def execute_sql_script(cursor, conn, sql_script):
    """Execute multiple SQL statements from a script"""
    # Split by semicolons and filter empty/comment-only chunks
    statements = [s.strip() for s in sql_script.split(';') if s.strip()]

    for statement in statements:
        # Skip pure comment blocks
        if statement.startswith('--') or not statement:
            continue

        # Skip legacy directives (just in case the old file is used)
        upper = statement.upper()
        if upper.startswith('DELIMITER') or upper.startswith('USE '):
            continue

        try:
            cursor.execute(statement)
            conn.commit()
            print(f"✓ Executed: {statement[:60]}...")
        except Error as e:
            conn.rollback()
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print(f"⚠ Skipped (already exists): {statement[:60]}...")
            else:
                print(f"✗ Error: {e}")
                print(f"  Statement: {statement[:120]}...")


def initialize_database():
    """Initialize the database with schema"""
    print("=" * 60)
    print("  Database Initialization for PoolGuard (PostgreSQL)")
    print("=" * 60)
    print()

    # Get database credentials
    print("Enter PostgreSQL connection details:")
    host = input("Host [localhost]: ").strip() or "localhost"
    port = input("Port [5432]: ").strip() or "5432"
    user = input("Username [postgres]: ").strip() or "postgres"
    password = input("Password: ").strip()
    dbname = input("Database [poolguard_db]: ").strip() or "poolguard_db"

    try:
        port = int(port)
    except ValueError:
        print("❌ Invalid port number!")
        return False

    print("\n🔄 Connecting to PostgreSQL...")

    connection = None
    try:
        connection = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname,
        )
        connection.autocommit = False
        print("✅ Connected to PostgreSQL server")
        cursor = connection.cursor()

        # Read and execute schema
        schema_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'schema.sql'
        )
        print("\n🔄 Reading schema.sql...")
        schema_sql = read_sql_file(schema_path)

        print("🔄 Executing database schema...")
        execute_sql_script(cursor, connection, schema_sql)

        connection.commit()
        print("\n✅ Database initialized successfully!")
        print("\n📝 Default Admin Credentials:")
        print("   Email: creagoouon@gmail.com")
        print("   Password: admin123")
        print("\n⚠️  IMPORTANT: Change the default password immediately!")
        print(f"\n💾 Connection string:")
        print(f"   postgresql://{user}:****@{host}:{port}/{dbname}")

    except Error as e:
        print(f"\n❌ Database error: {e}")
        return False

    finally:
        if connection:
            cursor.close()
            connection.close()
            print("\n🔌 Database connection closed")

    return True


if __name__ == "__main__":
    try:
        success = initialize_database()
        if success:
            print("\n✅ Setup complete! You can now start the application.")
            sys.exit(0)
        else:
            print("\n❌ Setup failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
