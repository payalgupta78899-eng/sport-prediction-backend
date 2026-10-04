from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class UserResponse(BaseModel):
    id         : int
    username   : str
    email      : str
    role       : str
    is_banned  : bool
    is_active  : bool
    created_at : datetime

    class Config:
        from_attributes = True


class UserUpdateRole(BaseModel):
    new_role : str

    class Config:
        from_attributes = True
