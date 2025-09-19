# Supabase Storage API Documentation

A comprehensive REST API for file storage and access control using Supabase backend.

## 🚀 Features

- **File Upload/Download** - Upload files with automatic metadata tracking
- **Access Control** - Granular permissions (read, write, owner)
- **Bucket Management** - Create and manage storage buckets
- **User Authentication** - JWT-based authentication
- **File Sharing** - Share files with other users
- **Automatic Cleanup** - Cascading deletion of permissions and metadata

## 📋 API Endpoints

| Method | Endpoint | Auth Required | Description |
|--------|----------|---------------|-------------|
| **GET** | `/health` | ❌ | Health check |
| **POST** | `/storage/buckets` | ✅ | Create storage bucket |
| **POST** | `/storage/files` | ✅ | Upload file |
| **GET** | `/storage/files` | ✅ | List user's accessible files |
| **GET** | `/storage/files/{file_id}` | ✅ | Get file details |
| **GET** | `/storage/files/{file_id}/download` | ✅ | Get download URL |
| **GET** | `/storage/files/{file_id}/redirect` | ✅ | Direct download redirect |
| **DELETE** | `/storage/files/{file_id}` | ✅ | Delete file (owner only) |
| **GET** | `/storage/files/{file_id}/access` | ✅ | Check file access level |
| **POST** | `/storage/files/{file_id}/access` | ✅ | Grant file access (owner only) |

**Auth Header Format**: `Authorization: Bearer {user_id_or_jwt_token}`

## 🔧 Request/Response Examples

### 1. Create Storage Bucket
```http
POST /storage/buckets
Authorization: Bearer your-user-id
Content-Type: application/json

{
  "bucket_name": "user-files",
  "public": false
}
```

**Response:**
```json
{
  "message": "Bucket 'user-files' created successfully",
  "success": true
}
```

### 2. Upload File
```http
POST /storage/files
Authorization: Bearer your-user-id
Content-Type: multipart/form-data

bucket_name: user-files
file: [binary file data]
custom_filename: my-document.pdf
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "my-document.pdf",
  "filepath": "user-id/20241225_143022_my-document.pdf",
  "file_size": 1024000,
  "content_type": "application/pdf",
  "created_at": "2024-12-25T14:30:22.123456Z",
  "updated_at": "2024-12-25T14:30:22.123456Z"
}
```

### 3. List User Files
```http
GET /storage/files
Authorization: Bearer your-user-id
```

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "my-document.pdf",
    "file_size": 1024000,
    "content_type": "application/pdf",
    "created_at": "2024-12-25T14:30:22.123456Z",
    "access_level": "owner"
  },
  {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "filename": "shared-file.txt",
    "file_size": 2048,
    "content_type": "text/plain",
    "created_at": "2024-12-25T13:20:15.789012Z",
    "access_level": "read"
  }
]
```

### 4. Get Download URL
```http
GET /storage/files/550e8400-e29b-41d4-a716-446655440000/download?bucket_name=user-files
Authorization: Bearer your-user-id
```

**Response:**
```json
{
  "download_url": "https://your-supabase-project.supabase.co/storage/v1/object/sign/user-files/user-id/20241225_143022_my-document.pdf?token=signed-token&t=2024-12-25T15%3A30%3A22.123Z",
  "expires_in": 3600
}
```

### 5. Grant File Access
```http
POST /storage/files/550e8400-e29b-41d4-a716-446655440000/access
Authorization: Bearer your-user-id
Content-Type: application/json

{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "target_user_id": "550e8400-e29b-41d4-a716-446655440001",
  "access_level": "read"
}
```

**Response:**
```json
{
  "message": "Successfully granted read access to user 550e8400-e29b-41d4-a716-446655440001",
  "success": true
}
```

### 6. Check File Access
```http
GET /storage/files/550e8400-e29b-41d4-a716-446655440000/access
Authorization: Bearer your-user-id
```

**Response:**
```json
{
  "access_level": "owner"
}
```

### 7. Delete File
```http
DELETE /storage/files/550e8400-e29b-41d4-a716-446655440000?bucket_name=user-files
Authorization: Bearer your-user-id
```

**Response:**
```json
{
  "message": "File deleted successfully",
  "success": true
}
```

## 🌐 Frontend Integration

### JavaScript/Fetch Example

```javascript
const API_URL = 'http://localhost:8000'; // Replace with your backend URL

class StorageService {
  constructor() {
    this.token = localStorage.getItem('access_token') || 'your-user-id';
  }

  async request(endpoint, options = {}) {
    const headers = { 
      ...options.headers,
      'Authorization': `Bearer ${this.token}`
    };
    
    // Don't set Content-Type for FormData (multipart/form-data)
    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(`${API_URL}${endpoint}`, { 
      ...options, 
      headers 
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Request failed');
    }

    return response.json();
  }

  // Create bucket
  async createBucket(bucketName, isPublic = false) {
    return this.request('/storage/buckets', {
      method: 'POST',
      body: JSON.stringify({
        bucket_name: bucketName,
        public: isPublic
      })
    });
  }

  // Upload file
  async uploadFile(bucketName, file, customFilename = null) {
    const formData = new FormData();
    formData.append('bucket_name', bucketName);
    formData.append('file', file);
    if (customFilename) {
      formData.append('custom_filename', customFilename);
    }

    return this.request('/storage/files', {
      method: 'POST',
      body: formData
    });
  }

  // List user files
  async listFiles() {
    return this.request('/storage/files');
  }

  // Get file details
  async getFileDetails(fileId) {
    return this.request(`/storage/files/${fileId}`);
  }

  // Get download URL
  async getDownloadUrl(fileId, bucketName) {
    return this.request(`/storage/files/${fileId}/download?bucket_name=${bucketName}`);
  }

  // Delete file
  async deleteFile(fileId, bucketName) {
    return this.request(`/storage/files/${fileId}?bucket_name=${bucketName}`, {
      method: 'DELETE'
    });
  }

  // Grant file access
  async grantAccess(fileId, targetUserId, accessLevel) {
    return this.request(`/storage/files/${fileId}/access`, {
      method: 'POST',
      body: JSON.stringify({
        file_id: fileId,
        target_user_id: targetUserId,
        access_level: accessLevel
      })
    });
  }

  // Check file access
  async checkAccess(fileId) {
    return this.request(`/storage/files/${fileId}/access`);
  }
}

// Usage example
const storage = new StorageService();

// Upload a file
document.getElementById('fileInput').addEventListener('change', async (event) => {
  const file = event.target.files[0];
  if (file) {
    try {
      const result = await storage.uploadFile('user-files', file);
      console.log('File uploaded:', result);
    } catch (error) {
      console.error('Upload failed:', error.message);
    }
  }
});
```

### React Hook Example

```jsx
import { useState, useCallback } from 'react';

const API_URL = 'http://localhost:8000';

const useStorage = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const token = localStorage.getItem('access_token') || 'your-user-id';

  const request = useCallback(async (endpoint, options = {}) => {
    setLoading(true);
    setError(null);

    try {
      const headers = { 
        ...options.headers,
        'Authorization': `Bearer ${token}`
      };
      
      if (!(options.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
      }

      const response = await fetch(`${API_URL}${endpoint}`, { 
        ...options, 
        headers 
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Request failed');
      }

      return await response.json();
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [token]);

  const uploadFile = useCallback(async (bucketName, file, customFilename = null) => {
    const formData = new FormData();
    formData.append('bucket_name', bucketName);
    formData.append('file', file);
    if (customFilename) {
      formData.append('custom_filename', customFilename);
    }

    return request('/storage/files', {
      method: 'POST',
      body: formData
    });
  }, [request]);

  const listFiles = useCallback(() => {
    return request('/storage/files');
  }, [request]);

  const deleteFile = useCallback((fileId, bucketName) => {
    return request(`/storage/files/${fileId}?bucket_name=${bucketName}`, {
      method: 'DELETE'
    });
  }, [request]);

  return {
    loading,
    error,
    uploadFile,
    listFiles,
    deleteFile,
    // ... other methods
  };
};

// Usage in component
const FileUploader = () => {
  const { uploadFile, listFiles, loading, error } = useStorage();
  const [files, setFiles] = useState([]);

  const handleUpload = async (event) => {
    const file = event.target.files[0];
    if (file) {
      try {
        await uploadFile('user-files', file);
        const updatedFiles = await listFiles();
        setFiles(updatedFiles);
      } catch (err) {
        console.error('Upload failed:', err.message);
      }
    }
  };

  return (
    <div>
      <input type="file" onChange={handleUpload} disabled={loading} />
      {error && <div className="error">Error: {error}</div>}
      {loading && <div>Loading...</div>}
      
      <div className="file-list">
        {files.map(file => (
          <div key={file.id} className="file-item">
            <span>{file.filename}</span>
            <span>({file.access_level})</span>
          </div>
        ))}
      </div>
    </div>
  );
};
```

## 📁 File Structure

```
project/
├── .env                    # Environment variables
├── storage_manager.py      # Core storage logic
├── main.py                # FastAPI application
├── database_schema.sql     # Database setup
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## 🔧 Setup Instructions

### 1. Install Dependencies
```bash
pip install fastapi uvicorn supabase python-dotenv python-multipart
```

### 2. Environment Variables
Create `.env` file:
```
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-public-key
```

### 3. Database Setup
Run the SQL schema in your Supabase SQL editor:
```sql
-- Copy contents from database_schema.sql
```

### 4. Run the API
```bash
python main.py
```

Or with uvicorn:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. API Documentation
Visit `http://localhost:8000/docs` for interactive API documentation.

## 🔒 Security Considerations

1. **Authentication**: Replace the simple token system with proper JWT authentication
2. **CORS**: Configure `allow_origins` appropriately for production
3. **File Validation**: Add file type and size validation
4. **Rate Limiting**: Implement rate limiting for file operations
5. **Input Sanitization**: Validate all user inputs
6. **Logging**: Ensure sensitive data is not logged

## 🐛 Error Handling

All endpoints return consistent error responses:

```json
{
  "error": "Error description",
  "success": false
}
```

Common HTTP status codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `409` - Conflict
- `500` - Internal Server Error

## 🚀 Production Deployment

### Using Docker
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Using Railway/Render/Heroku
Create `Procfile`:
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Environment Variables (Production)
```bash
SUPABASE_URL=your_production_supabase_url
SUPABASE_KEY=your_production_anon_key
PORT=8000
```

## 📊 Performance & Monitoring

### File Size Limits
- Default: No explicit limit (controlled by FastAPI)
- Recommended: Add size validation in production
- Supabase storage limit: Check your plan limits

### Concurrent Uploads
- FastAPI handles concurrent requests efficiently
- Consider implementing queue system for large files
- Monitor Supabase storage API rate limits

### Logging & Monitoring
```python
import logging
from datetime import datetime

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('storage_api.log'),
        logging.StreamHandler()
    ]
)

# Track API metrics
class APIMetrics:
    def __init__(self):
        self.upload_count = 0
        self.download_count = 0
        self.error_count = 0
        
    def track_upload(self):
        self.upload_count += 1
        
    def track_download(self):
        self.download_count += 1
        
    def track_error(self):
        self.error_count += 1
```

## 🧪 Testing

### Unit Tests Example
```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "Supabase Storage API"}

def test_upload_file():
    # Mock file upload
    files = {"file": ("test.txt", "test content", "text/plain")}
    data = {"bucket_name": "test-bucket"}
    headers = {"Authorization": "Bearer test-user-id"}
    
    response = client.post("/storage/files", files=files, data=data, headers=headers)
    assert response.status_code == 200

def test_unauthorized_access():
    response = client.get("/storage/files")
    assert response.status_code == 401
```

### Integration Tests
```python
import requests
import tempfile
import os

class TestStorageAPI:
    def __init__(self, base_url, user_token):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {user_token}"}
    
    def test_complete_workflow(self):
        # 1. Create bucket
        bucket_response = requests.post(
            f"{self.base_url}/storage/buckets",
            json={"bucket_name": "test-bucket", "public": False},
            headers=self.headers
        )
        assert bucket_response.status_code == 200
        
        # 2. Upload file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test file content")
            temp_path = f.name
        
        with open(temp_path, 'rb') as f:
            files = {"file": ("test.txt", f, "text/plain")}
            data = {"bucket_name": "test-bucket"}
            upload_response = requests.post(
                f"{self.base_url}/storage/files",
                files=files,
                data=data,
                headers=self.headers
            )
        
        os.unlink(temp_path)
        assert upload_response.status_code == 200
        file_data = upload_response.json()
        file_id = file_data["id"]
        
        # 3. List files
        list_response = requests.get(
            f"{self.base_url}/storage/files",
            headers=self.headers
        )
        assert list_response.status_code == 200
        files = list_response.json()
        assert len(files) > 0
        
        # 4. Get download URL
        download_response = requests.get(
            f"{self.base_url}/storage/files/{file_id}/download",
            params={"bucket_name": "test-bucket"},
            headers=self.headers
        )
        assert download_response.status_code == 200
        
        # 5. Delete file
        delete_response = requests.delete(
            f"{self.base_url}/storage/files/{file_id}",
            params={"bucket_name": "test-bucket"},
            headers=self.headers
        )
        assert delete_response.status_code == 200

# Usage
test_api = TestStorageAPI("http://localhost:8000", "test-user-id")
test_api.test_complete_workflow()
```

## 🔧 Advanced Configuration

### Custom File Validation
```python
from typing import List
import magic

ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

async def validate_file(file: UploadFile) -> bool:
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type {file_ext} not allowed")
    
    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Seek back to start
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(400, f"File size {file_size} exceeds maximum {MAX_FILE_SIZE}")
    
    # Check MIME type using python-magic (optional)
    file_content = await file.read()
    file.file.seek(0)  # Reset for later use
    
    detected_type = magic.from_buffer(file_content, mime=True)
    # Add MIME type validation logic here
    
    return True
```

### Database Connection Pooling
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

# For direct PostgreSQL connections (optional)
DATABASE_URL = "postgresql://user:password@localhost/dbname"

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)
```

### Async File Processing
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

async def async_file_upload(user_id: str, local_path: str, bucket_name: str):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor,
        storage_manager.upload_file,
        user_id,
        local_path,
        bucket_name
    )
```

## 📈 Scaling Considerations

### Horizontal Scaling
- Deploy multiple API instances behind a load balancer
- Use Redis for session management if implementing real sessions
- Consider CDN for file delivery

### Database Optimization
```sql
-- Additional indexes for better performance
CREATE INDEX CONCURRENTLY idx_files_user_created 
ON files(user_id, created_at DESC);

CREATE INDEX CONCURRENTLY idx_permissions_compound 
ON file_permissions(user_id, access_level, file_id);

-- Partitioning for large datasets
CREATE TABLE files_2024 PARTITION OF files 
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

### Caching Strategy
```python
from functools import lru_cache
import redis

# Redis for distributed caching
redis_client = redis.Redis(host='localhost', port=6379, db=0)

@lru_cache(maxsize=1000)
def get_user_permissions(user_id: str, file_id: str):
    # Cache permission checks
    cache_key = f"perm:{user_id}:{file_id}"
    cached = redis_client.get(cache_key)
    if cached:
        return cached.decode()
    
    # Fetch from database and cache
    result = storage_manager.check_access(user_id, file_id)
    redis_client.setex(cache_key, 300, result or "none")  # 5 min cache
    return result
```

## 🛠️ Troubleshooting

### Common Issues

1. **"Bucket not found" errors**
   ```bash
   # Check if bucket exists in Supabase dashboard
   # Ensure bucket name matches exactly (case-sensitive)
   ```

2. **Authentication failures**
   ```bash
   # Verify SUPABASE_URL and SUPABASE_KEY in .env
   # Check if RLS policies are properly configured
   ```

3. **File upload timeouts**
   ```python
   # Increase timeout in FastAPI
   from fastapi import FastAPI
   app = FastAPI(timeout=300)  # 5 minutes
   ```

4. **Permission denied errors**
   ```sql
   -- Check RLS policies in Supabase
   SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual 
   FROM pg_policies 
   WHERE tablename IN ('files', 'file_permissions');
   ```

### Debug Mode
```python
import os
os.environ['DEBUG'] = 'True'

if os.getenv('DEBUG'):
    logging.getLogger().setLevel(logging.DEBUG)
    # Enable detailed SQL logging
    logging.getLogger('supabase').setLevel(logging.DEBUG)
```

## 📚 Additional Resources

- [Supabase Storage Documentation](https://supabase.com/docs/guides/storage)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL Row Level Security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [JWT Authentication Best Practices](https://auth0.com/blog/a-look-at-the-latest-draft-for-jwt-bcp/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**⚠️ Important Notes:**
- Replace the simple user authentication with proper JWT validation in production
- Configure CORS origins appropriately for your frontend domain
- Set up proper logging and monitoring in production
- Regular backup of your Supabase database
- Monitor storage usage and implement cleanup policies for old files