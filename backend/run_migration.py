"""Run database migration to add deployment fields to conversations table."""
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.snowflake import exec_query

def run_migration():
    """Add deployment tracking fields to conversations table."""
    print("Running migration: Add deployment fields to conversations table...")
    
    try:
        # Add is_deployed column
        exec_query("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS is_deployed BOOLEAN DEFAULT FALSE")
        print("✓ Added is_deployed column")
        
        # Add deployment_id column
        exec_query("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS deployment_id STRING")
        print("✓ Added deployment_id column")
        
        # Add tasklist_id column
        exec_query("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS tasklist_id STRING")
        print("✓ Added tasklist_id column")
        
        # Add deployed_at column
        exec_query("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS deployed_at TIMESTAMP_NTZ")
        print("✓ Added deployed_at column")
        
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
