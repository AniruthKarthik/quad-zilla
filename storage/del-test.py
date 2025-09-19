
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Initialize Supabase
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

bucket_name = "test-bucket"

try:
    files = supabase.storage.from_(bucket_name).list()
    if not files:
        print(f"No files found in bucket {bucket_name}")
    else:
        file_paths = [file['name'] for file in files]
        supabase.storage.from_(bucket_name).remove(file_paths)
        print(f"Successfully deleted all files from bucket {bucket_name}")
except Exception as e:
    print(f"Error deleting files: {e}")
