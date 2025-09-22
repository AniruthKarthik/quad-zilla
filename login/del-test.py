from supabase import create_client
import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Check if environment variables are loaded
if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL or SUPABASE_KEY not found in environment variables")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    # Delete all rows using the correct column name (uid is a bigint)
    # Using a condition that will match all rows
    response = supabase.table("users").delete().gte("uid", 0).execute()
    print(f"All rows in 'users' table have been deleted. Affected rows: {len(response.data)}")
except Exception as e:
    print(f"Error deleting rows: {e}")
    
    # If the above fails, try alternative methods
    print("Trying alternative deletion methods...")
    
    try:
        # Alternative 1: Use not equal to a non-existent ID
        response = supabase.table("users").delete().neq("uid", -1).execute()
        print(f"Alternative method worked. Affected rows: {len(response.data)}")
    except Exception as e2:
        print(f"Alternative method also failed: {e2}")
        
        try:
            # Alternative 2: Use greater than or equal to minimum value
            response = supabase.table("users").delete().gte("uid", -999999999).execute()
            print(f"Second alternative worked. Affected rows: {len(response.data)}")
        except Exception as e3:
            print(f"All methods failed: {e3}")
