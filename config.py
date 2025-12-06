import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    BASE_DIR: Path = Path(__file__).parent
    DOCUMENTS_PATH: Path = Path(os.getenv("DOCUMENTS_PATH", "./documents"))

    @classmethod
    def validate(cls) -> bool:
        errors = []

        if not cls.SUPABASE_URL:
            errors.append("SUPABASE_URL is not set")

        if not cls.SUPABASE_SERVICE_ROLE_KEY:
            errors.append("SUPABASE_SERVICE_ROLE_KEY is not set")

        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is not set")

        if errors:
            print("Configuration errors:")
            for error in errors:
                print(f"   - {error}")
            return False

        print("Configuration validated successfully")
        return True


config = Config()
