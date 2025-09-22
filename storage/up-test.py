
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Initialize Supabase
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

bucket_name = "test-bucket"
file_path = "dummy.txt"
remote_file_path = "dummy.txt"

try:
    with open(file_path, 'rb') as f:
        supabase.storage.from_(bucket_name).upload(remote_file_path, f)
    print(f"Successfully uploaded {file_path} to {bucket_name}/{remote_file_path}")
except Exception as e:
    print(f"Error uploading file: {e}")
