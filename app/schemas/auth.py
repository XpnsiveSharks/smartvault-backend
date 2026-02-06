from __future__ import annotations
from pydantic import BaseModel, EmailStr, Field

class OTPRequest(BaseModel):
    email: EmailStr

class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)

class OTPVerifyResponse(BaseModel):
    signup_ticket: str

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    full_name: str | None = Field(default=None, max_length=200)
    signup_ticket: str = Field(min_length=20)  

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    
class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str
    expires_in: int = 1800

class RefreshRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    refresh_token: str