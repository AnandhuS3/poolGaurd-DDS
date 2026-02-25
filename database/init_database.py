"""
Database Initialization Script
Run this script to set up the MySQL database and create the initial admin user
"""
import mysql.connector
from mysql.connector import Error
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def read_sql_file(filename):
    """Read SQL file and return contents"""
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

def execute_sql_script(cursor, sql_script):
    """Execute multiple SQL statements from a script"""
    # Split by semicolon and filter empty statements
    statements = [s.strip() for s in sql_script.split(';') if s.strip()]
    
    for statement in statements:
        # Skip comments and empty lines
        if statement.startswith('--') or not statement:
            continue
        
        # Handle DELIMITER statements for stored procedures
        if 'DELIMITER' in statement.upper():
            continue
            
        try:
            cursor.execute(statement)
            print(f"✓ Executed: {statement[:50]}...")
        except Error as e:
            # Continue on some expected errors
            if "already exists" in str(e).lower():
                print(f"⚠ Skipped (already exists): {statement[:50]}...")
            else:
                print(f"✗ Error: {e}")
                print(f"  Statement: {statement[:100]}...")

def initialize_database():
    """Initialize the database with schema"""
    print("=" * 60)
    print("  Database Initialization for Drowning Detection System")
    print("=" * 60)
    print()
    
    # Get database credentials
    print("Enter MySQL connection details:")
    host = input("Host [localhost]: ").strip() or "localhost"
    port = input("Port [3306]: ").strip() or "3306"
    user = input("Username [root]: ").strip() or "root"
    password = input("Password: ").strip()
    
    try:
        port = int(port)
    except ValueError:
        print("❌ Invalid port number!")
        return
    
    print("\n🔄 Connecting to MySQL...")
    
    try:
        # Connect to MySQL server (without database)
        connection = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password
        )
        
        if connection.is_connected():
            print("✅ Connected to MySQL server")
            cursor = connection.cursor()
            
            # Read and execute schema
            print("\n🔄 Reading schema.sql...")
            schema_sql = read_sql_file('database/schema.sql')
            
            print("🔄 Executing database schema...")
            execute_sql_script(cursor, schema_sql)
            
            connection.commit()
            print("\n✅ Database initialized successfully!")
            print("\n📝 Default Admin Credentials:")
            print("   Email: admin@dds.local")
            print("   Password: admin123")
            print("\n⚠️  IMPORTANT: Change the default password immediately!")
            print("\n💾 Update your config.py with these settings:")
            print(f"   DB_HOST = \"{host}\"")
            print(f"   DB_PORT = {port}")
            print(f"   DB_USER = \"{user}\"")
            print(f"   DB_PASSWORD = \"{password}\"")
            print(f"   DB_NAME = \"drowning_detection_db\"")
            
    except Error as e:
        print(f"\n❌ Database error: {e}")
        return False
    
    finally:
        if connection and connection.is_connected():
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
