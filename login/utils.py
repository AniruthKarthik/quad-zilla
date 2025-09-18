import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from .config import settings
from .db import supabase

logger = logging.getLogger(__name__)

def send_email(to_email: str, subject: str, body: str, is_html: bool = False) -> bool:
    """
    Send email using SMTP
    Args:
        to_email: Recipient email
        subject: Email subject
        body: Email body
        is_html: Whether body is HTML or plain text
    Returns: True if email sent successfully, False otherwise
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = settings.EMAIL_USER
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html' if is_html else 'plain'))
        
        server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False

def send_password_reset_email(email: str, username: str, reset_token: str) -> bool:
    """Send password reset email"""
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Password Reset Request</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #f8f9fa; padding: 20px; text-align: center; }}
            .content {{ background-color: #fff; padding: 30px; border: 1px solid #dee2e6; }}
            .button {{ display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 4px; }}
            .footer {{ margin-top: 20px; padding: 20px; text-align: center; font-size: 12px; color: #6c757d; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{settings.APP_NAME}</h1>
            </div>
            <div class="content">
                <h2>Password Reset Request</h2>
                <p>Hello {username},</p>
                <p>We received a request to reset your password. If you didn't make this request, you can safely ignore this email.</p>
                <p>To reset your password, click the button below:</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}" class="button">Reset Password</a>
                </p>
                <p>Or copy and paste this link in your browser:</p>
                <p style="word-break: break-all; color: #007bff;">{reset_link}</p>
                <p><strong>This link will expire in {settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS} hour(s).</strong></p>
            </div>
            <div class="footer">
                <p>If you're having trouble clicking the button, copy and paste the URL into your web browser.</p>
                <p>This is an automated message, please do not reply to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_email(email, "Password Reset Request", html_body, is_html=True)

def send_welcome_email(email: str, username: str) -> bool:
    """Send welcome email to new users"""
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Welcome to {settings.APP_NAME}</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #28a745; padding: 20px; text-align: center; color: white; }}
            .content {{ background-color: #fff; padding: 30px; border: 1px solid #dee2e6; }}
            .footer {{ margin-top: 20px; padding: 20px; text-align: center; font-size: 12px; color: #6c757d; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Welcome to {settings.APP_NAME}!</h1>
            </div>
            <div class="content">
                <h2>Hello {username},</h2>
                <p>Thank you for creating an account with {settings.APP_NAME}. We're excited to have you on board!</p>
                <p>Your account has been successfully created and is ready to use.</p>
                <p>If you have any questions or need assistance, please don't hesitate to contact our support team.</p>
                <p>Best regards,<br>The {settings.APP_NAME} Team</p>
            </div>
            <div class="footer">
                <p>This is an automated message, please do not reply to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_email(email, f"Welcome to {settings.APP_NAME}!", html_body, is_html=True)

def log_login_attempt(identifier: str, ip_address: str, success: bool) -> bool:
    """Log login attempt for security monitoring"""
    try:
        supabase.table("login_attempts").insert({
            "identifier": identifier,
            "ip_address": ip_address,
            "success": success,
            "attempt_time": datetime.utcnow().isoformat()
        }).execute()
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to log login attempt: {str(e)}")
        return False

def check_rate_limit(identifier: str, ip_address: str) -> Dict[str, Any]:
    """
    Check if user/IP is rate limited
    Returns: dict with 'allowed' boolean and 'retry_after' seconds if blocked
    """
    try:
        # Check attempts in last 15 minutes
        time_window = (datetime.utcnow() - timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)).isoformat()
        
        # Count failed attempts by identifier
        identifier_attempts = supabase.table("login_attempts")\
            .select("*")\
            .eq("identifier", identifier)\
            .eq("success", False)\
            .gte("attempt_time", time_window)\
            .execute()
        
        # Count failed attempts by IP
        ip_attempts = supabase.table("login_attempts")\
            .select("*")\
            .eq("ip_address", ip_address)\
            .eq("success", False)\
            .gte("attempt_time", time_window)\
            .execute()
        
        identifier_count = len(identifier_attempts.data) if identifier_attempts.data else 0
        ip_count = len(ip_attempts.data) if ip_attempts.data else 0
        
        # Check if either identifier or IP exceeded limit
        if identifier_count >= settings.MAX_LOGIN_ATTEMPTS or ip_count >= settings.MAX_LOGIN_ATTEMPTS:
            return {
                "allowed": False,
                "retry_after": settings.LOCKOUT_DURATION_MINUTES * 60,
                "message": f"Too many failed attempts. Try again in {settings.LOCKOUT_DURATION_MINUTES} minutes."
            }
        
        return {"allowed": True}
        
    except Exception as e:
        logger.error(f"Error checking rate limit: {str(e)}")
        # Allow on error to prevent blocking legitimate users
        return {"allowed": True}

def generate_user_stats(user_id: str) -> Dict[str, Any]:
    """Generate user statistics"""
    try:
        # Get user info
        user = supabase.table("users").select("*").eq("id", user_id).single().execute()
        
        if not user.data:
            return {"error": "User not found"}
        
        # Get login attempts count
        login_attempts = supabase.table("login_attempts")\
            .select("*")\
            .eq("identifier", user.data["username"])\
            .execute()
        
        successful_logins = len([attempt for attempt in login_attempts.data if attempt["success"]]) if login_attempts.data else 0
        failed_logins = len([attempt for attempt in login_attempts.data if not attempt["success"]]) if login_attempts.data else 0
        
        # Calculate account age
        created_at = datetime.fromisoformat(user.data["created_at"].replace('Z', '+00:00'))
        account_age_days = (datetime.now(created_at.tzinfo) - created_at).days
        
        return {
            "user_id": user_id,
            "username": user.data["username"],
            "email": user.data["email"],
            "account_created": user.data["created_at"],
            "account_age_days": account_age_days,
            "last_login": user.data.get("last_login"),
            "is_active": user.data["is_active"],
            "total_successful_logins": successful_logins,
            "total_failed_logins": failed_logins
        }
        
    except Exception as e:
        logger.error(f"Error generating user stats: {str(e)}")
        return {"error": "Failed to generate user statistics"}

def sanitize_user_input(input_string: str) -> str:
    """Sanitize user input to prevent XSS and other attacks"""
    import html
    
    if not isinstance(input_string, str):
        return ""
    
    # HTML escape
    sanitized = html.escape(input_string.strip())
    
    # Remove any potentially dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '&', '\x00']
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')
    
    return sanitized

def mask_email(email: str) -> str:
    """Mask email for privacy (e.g., user@example.com -> u***@example.com)"""
    if '@' not in email:
        return email
    
    local, domain = email.split('@', 1)
    
    if len(local) <= 2:
        masked_local = local[0] + '*' * (len(local) - 1)
    else:
        masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
    
    return f"{masked_local}@{domain}"

def validate_ip_address(ip: str) -> bool:
    """Validate IP address format"""
    import ipaddress
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False