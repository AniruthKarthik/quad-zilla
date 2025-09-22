from supabase import create_client
import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Test: get all rows from "users" table
response = supabase.table("users").select("*").execute()
print("All users:", response.data)

# Test: insert a new row
insert_response = supabase.table("users").insert({"username": "ani", "password_hash": "test123"}).execute()
print("Insert result:", insert_response.data)

