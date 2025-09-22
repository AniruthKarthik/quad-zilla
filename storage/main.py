"""
FastAPI REST API for Supabase Storage Manager
Provides comprehensive file storage and access control endpoints.
"""

from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File, Form, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import tempfile
import os
import logging
from storage_manager import StorageManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Supabase Storage API",
    description="A comprehensive file storage and access control system using Supabase",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security scheme
security = HTTPBearer()

# Initialize storage manager
storage_manager = StorageManager()

# Pydantic models
class AccessGrantRequest(BaseModel):
    file_id: str = Field(..., description="UUID of the file")
    target_user_id: str = Field(..., description="UUID of user to grant access to")
    access_level: str = Field(..., description="Access level to grant", regex="^(read|write)$")

class BucketCreateRequest(BaseModel):
    bucket_name: str = Field(..., description="Name of the bucket to create")
    public: bool = Field(default=False, description="Whether the bucket should be public")

class FileResponse(BaseModel):
    id: str
    filename: str
    filepath: str
    file_size: Optional[int]
    content_type: Optional[str]
    created_at: str
    updated_at: Optional[str]

class AccessResponse(BaseModel):
    access_level: Optional[str] = Field(description="User's access level or null if no access")

class FileListResponse(BaseModel):
    id: str
    filename: str
    file_size: Optional[int]
    content_type: Optional[str]
    created_at: str
    access_level: str

class DownloadResponse(BaseModel):
    download_url: str
    expires_in: int = Field(default=3600, description="URL expiry time in seconds")

class SuccessResponse(BaseModel):
    message: str
    success: bool = True

class ErrorResponse(BaseModel):
    error: str
    success: bool = False

# Dependency to extract user_id from Authorization header
async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Extract user ID from JWT token or use token as user ID.
    In a real application, you would decode the JWT token to get the user ID.
    For this example, we'll use the token as the user ID directly.
    """
    token = credentials.credentials
    
    # TODO: Replace this with actual JWT token decoding
    # For now, we'll assume the token IS the user ID
    # In production, you would:
    # 1. Decode the JWT token
    # 2. Extract the user ID from the token payload
    # 3. Verify the token is valid and not expired
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return token

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Supabase Storage API"}

# Bucket management endpoints
@app.post("/storage/buckets", response_model=SuccessResponse, tags=["Bucket Management"])
async def create_bucket(
    request: BucketCreateRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    """Create a new storage bucket"""
    try:
        success = storage_manager.create_storage_bucket(
            bucket_name=request.bucket_name,
            public=request.public
        )
        
        if success:
            logger.info(f"User {current_user_id} created bucket '{request.bucket_name}'")
            return SuccessResponse(message=f"Bucket '{request.bucket_name}' created successfully")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create bucket '{request.bucket_name}'"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bucket creation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during bucket creation"
        )

# File upload endpoint
@app.post("/storage/files", response_model=FileResponse, tags=["File Operations"])
async def upload_file(
    bucket_name: str = Form(..., description="Name of the storage bucket"),
    file: UploadFile = File(..., description="File to upload"),
    custom_filename: Optional[str] = Form(None, description="Custom filename for the uploaded file"),
    current_user_id: str = Depends(get_current_user_id)
):
    """Upload a file to storage"""
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Upload file
        file_record = storage_manager.upload_file(
            user_id=current_user_id,
            local_path=temp_file_path,
            bucket_name=bucket_name,
            remote_filename=custom_filename or file.filename
        )
        
        # Clean up temporary file
        os.unlink(temp_file_path)
        
        if file_record:
            logger.info(f"User {current_user_id} uploaded file '{file.filename}' to bucket '{bucket_name}'")
            return FileResponse(**file_record)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to upload file"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        # Clean up temporary file if it exists
        try:
            if 'temp_file_path' in locals():
                os.unlink(temp_file_path)
        except:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during file upload"
        )

# File download endpoint
@app.get("/storage/files/{file_id}/download", response_model=DownloadResponse, tags=["File Operations"])
async def get_download_url(
    file_id: str,
    bucket_name: str = Query(..., description="Name of the storage bucket"),
    current_user_id: str = Depends(get_current_user_id)
):
    """Get signed download URL for a file"""
    try:
        download_url = storage_manager.fetch_file(
            user_id=current_user_id,
            file_id=file_id,
            bucket_name=bucket_name
        )
        
        if download_url:
            logger.info(f"Generated download URL for file {file_id} for user {current_user_id}")
            return DownloadResponse(download_url=download_url)
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied or file not found"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download URL generation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during download URL generation"
        )

# Direct file download redirect
@app.get("/storage/files/{file_id}/redirect", tags=["File Operations"])
async def download_file_redirect(
    file_id: str,
    bucket_name: str = Query(..., description="Name of the storage bucket"),
    current_user_id: str = Depends(get_current_user_id)
):
    """Redirect directly to the file download URL"""
    try:
        download_url = storage_manager.fetch_file(
            user_id=current_user_id,
            file_id=file_id,
            bucket_name=bucket_name
        )
        
        if download_url:
            return RedirectResponse(url=download_url, status_code=302)
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied or file not found"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File redirect error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during file redirect"
        )

# File deletion endpoint
@app.delete("/storage/files/{file_id}", response_model=SuccessResponse, tags=["File Operations"])
async def delete_file(
    file_id: str,
    bucket_name: str = Query(..., description="Name of the storage bucket"),
    current_user_id: str = Depends(get_current_user_id)
):
    """Delete a file (owner only)"""
    try:
        success = storage_manager.delete_file(
            user_id=current_user_id,
            file_id=file_id,
            bucket_name=bucket_name
        )
        
        if success:
            logger.info(f"User {current_user_id} deleted file {file_id}")
            return SuccessResponse(message="File deleted successfully")
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied - only file owners can delete files"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File deletion error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during file deletion"
        )

# Access control endpoints
@app.get("/storage/files/{file_id}/access", response_model=AccessResponse, tags=["Access Control"])
async def check_file_access(
    file_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Check user's access level for a specific file"""
    try:
        access_level = storage_manager.check_access(
            user_id=current_user_id,
            file_id=file_id
        )
        
        return AccessResponse(access_level=access_level)
    
    except Exception as e:
        logger.error(f"Access check error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during access check"
        )

@app.post("/storage/files/{file_id}/access", response_model=SuccessResponse, tags=["Access Control"])
async def grant_file_access(
    file_id: str,
    request: AccessGrantRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    """Grant access to a file (owner only)"""
    try:
        # Ensure the file_id in URL matches the request body
        if file_id != request.file_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File ID in URL must match file ID in request body"
            )
        
        success = storage_manager.grant_access(
            owner_user_id=current_user_id,
            file_id=request.file_id,
            target_user_id=request.target_user_id,
            access_level=request.access_level
        )
        
        if success:
            logger.info(f"User {current_user_id} granted {request.access_level} access to user {request.target_user_id} for file {file_id}")
            return SuccessResponse(
                message=f"Successfully granted {request.access_level} access to user {request.target_user_id}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied - only file owners can grant access"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Access grant error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during access grant"
        )

# File listing endpoints
@app.get("/storage/files", response_model=List[FileListResponse], tags=["File Operations"])
async def list_user_files(
    current_user_id: str = Depends(get_current_user_id)
):
    """List all files accessible to the current user"""
    try:
        files = storage_manager.list_user_files(current_user_id)
        
        response_files = []
        for file_info in files:
            response_files.append(FileListResponse(**file_info))
        
        logger.info(f"Listed {len(files)} files for user {current_user_id}")
        return response_files
    
    except Exception as e:
        logger.error(f"File listing error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during file listing"
        )

@app.get("/storage/files/{file_id}", response_model=FileResponse, tags=["File Operations"])
async def get_file_details(
    file_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get detailed information about a specific file"""
    try:
        # Check if user has access to the file
        access_level = storage_manager.check_access(current_user_id, file_id)
        if not access_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get file details from database
        file_result = storage_manager.supabase.table('files').select('*').eq('id', file_id).execute()
        
        if not file_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        file_record = file_result.data[0]
        return FileResponse(**file_record)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File details error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during file details retrieval"
        )

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "success": False}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler for unhandled exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "success": False}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)