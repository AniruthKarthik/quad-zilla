
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Initialize Supabase
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

bucket_name = "user-files"
remote_file_path = "dummy.txt"
download_path = "downloaded_dummy.txt"

try:
    with open(download_path, 'wb+') as f:
        res = supabase.storage.from_(bucket_name).download(remote_file_path)
        f.write(res)
    print(f"Successfully downloaded {remote_file_path} to {download_path}")
except Exception as e:
    print(f"Error downloading file: {e}")
