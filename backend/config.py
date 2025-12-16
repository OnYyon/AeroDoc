from pydantic_settings import BaseSettings
from typing import List, Union


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./aerodoc.db"
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 дней
    
    # CORS - используем Union для совместимости
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Documents
    DOCUMENTS_DIR: str = "./documents"
    
    # ML Service
    ML_SERVICE_URL: str = "http://localhost:8001/api/ml/process"
    
    class Config:
        env_file = ".env"
        
    def get_cors_origins(self):
        """Получить список CORS origins в правильном формате"""
        if isinstance(self.CORS_ORIGINS, str):
            return [self.CORS_ORIGINS]
        return self.CORS_ORIGINS


settings = Settings()

