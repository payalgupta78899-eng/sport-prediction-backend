from pydantic import BaseModel, EmailStr, field_validator
import re


class RegisterRequest(BaseModel):
    username : str
    email    : EmailStr
    password : str

    @field_validator("username")
    def username_valid(cls, v):
        if len(v) < 3 or len(v) > 30:
            raise ValueError("Username must be 3-30 characters")
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Username can only contain letters, numbers, underscores")
        return v.lower()

    @field_validator("password")
    def password_strong(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one number")
        return v


class LoginRequest(BaseModel):
    username : str
    password : str


class TokenResponse(BaseModel):
    access_token : str
    token_type   : str = "bearer"
    # refresh token sent as httpOnly cookie — not in response body


class RefreshResponse(BaseModel):
    access_token : str
    token_type   : str = "bearer"


class ChangePasswordRequest(BaseModel):
    current_password : str
    new_password     : str

    @field_validator("new_password")
    def password_strong(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v
