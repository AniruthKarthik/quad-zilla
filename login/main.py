from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from .models import (
    RegisterRequest, LoginRequest, ChangePasswordRequest, 
    ResetPasswordRequest, UserResponse, TokenResponse
)
from .auth import (
    register_user, authenticate_user, get_current_user,
    create_access_token, verify_token, change_user_password,
    initiate_password_reset, reset_password_with_token,
    deactivate_user, get_user_profile
)
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Enhanced Authentication API",
    description="A comprehensive authentication system with JWT tokens",
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

async def get_current_user_dependency(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current user from JWT token"""
    user = get_current_user(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token or user not found",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user

@app.post("/auth/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest):
    """Register a new user"""
    try:
        result = register_user(req.username, req.email, req.password)
        if "error" in result:
            if "already exists" in result["error"].lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=result["error"]
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result["error"]
                )
        
        logger.info(f"User {req.username} registered successfully")
        return {
            "message": "User registered successfully",
            "user_id": result["id"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during registration"
        )

@app.post("/auth/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """Authenticate user and return JWT token"""
    try:
        user = authenticate_user(req.username, req.password)
        if not user:
            logger.warning(f"Failed login attempt for username: {req.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )
        
        access_token = create_access_token(data={"sub": str(user["id"])})
        logger.info(f"User {user['username']} logged in successfully")
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                id=user["id"],
                username=user["username"],
                email=user["email"],
                is_active=user.get("is_active", True),
                created_at=user.get("created_at")
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )

@app.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user_dependency)):
    """Get current user profile"""
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        is_active=current_user.get("is_active", True),
        created_at=current_user.get("created_at")
    )

@app.post("/auth/change-password")
async def change_password(
    req: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user_dependency)
):
    """Change user password"""
    try:
        result = change_user_password(
            current_user["id"],
            req.current_password,
            req.new_password
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        logger.info(f"Password changed for user {current_user['username']}")
        return {"message": "Password changed successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during password change"
        )

@app.post("/auth/forgot-password")
async def forgot_password(req: ResetPasswordRequest):
    """Initiate password reset process"""
    try:
        result = initiate_password_reset(req.email)
        # Always return success to prevent email enumeration
        return {"message": "If the email exists, a reset link has been sent"}
    
    except Exception as e:
        logger.error(f"Password reset initiation error: {str(e)}")
        return {"message": "If the email exists, a reset link has been sent"}

@app.post("/auth/reset-password/{token}")
async def reset_password(token: str, new_password: str):
    """Reset password using token"""
    try:
        result = reset_password_with_token(token, new_password)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return {"message": "Password reset successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during password reset"
        )

@app.post("/auth/logout")
async def logout(current_user: dict = Depends(get_current_user_dependency)):
    """Logout user (client should discard token)"""
    logger.info(f"User {current_user['username']} logged out")
    return {"message": "Logged out successfully"}

@app.delete("/auth/deactivate")
async def deactivate_account(current_user: dict = Depends(get_current_user_dependency)):
    """Deactivate user account"""
    try:
        result = deactivate_user(current_user["id"])
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        logger.info(f"Account deactivated for user {current_user['username']}")
        return {"message": "Account deactivated successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Account deactivation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during account deactivation"
        )

@app.get("/auth/validate-token")
async def validate_token(current_user: dict = Depends(get_current_user_dependency)):
    """Validate JWT token"""
    return {"valid": True, "user_id": current_user["id"]}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}