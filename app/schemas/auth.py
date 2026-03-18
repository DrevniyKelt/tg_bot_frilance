from pydantic import BaseModel


class TelegramVerifyRequest(BaseModel):
    init_data: str


class AuthResponse(BaseModel):
    user_id: int
    display_name: str
    locale: str
