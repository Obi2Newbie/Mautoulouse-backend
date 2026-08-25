from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str               # anon key  (public)
    supabase_service_key: str       # service role (bypass RLS — admin ops)
    supabase_jwt_secret: str        # from Supabase dashboard → Settings → API

    class Config:
        env_file = ".env"


settings = Settings()
