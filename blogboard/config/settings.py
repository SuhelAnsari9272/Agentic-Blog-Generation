from typing import Optional, Dict
from pydantic import BaseModel, Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict

class LLMSettings(BaseModel):
    API_KEY: str = Field(validation_alias=AliasChoices('API_KEY', 'api_key', 'GROQ_API_KEY', 'groq_api_key'))
    MODEL_NAME: str = "llama-3.3-70b-versatile"
    TEMPERATURE: float = 1.0

class TagSettings(BaseModel):
    ml: Dict[str, str] = {"label": "Machine Learning", "shortLabel": "ML"}
    dl: Dict[str, str] = {"label": "Deep Learning", "shortLabel": "DL"}
    statistics: Dict[str, str] = {"label": "Statistics for AI", "shortLabel": "Stats"}
    nlp: Dict[str, str] = {"label": "Natural Language Processing", "shortLabel": "NLP"}
    cv: Dict[str, str] = {"label": "Computer Vision", "shortLabel": "CV"}
    genai: Dict[str, str] = {"label": "Generative AI", "shortLabel": "Gen AI"}
    ainews: Dict[str, str] = {"label": "AI News", "shortLabel": "AI News"}

class R2Settings(BaseModel):
    ACCOUNT_ID: str
    ACCESS_KEY_ID: str
    SECRET_ACCESS_KEY: str
    BUCKET_NAME: str

class StorageSettings(BaseModel):
    TYPE: str = Field("local", validation_alias=AliasChoices('TYPE', 'type', 'STORAGE_TYPE', 'storage_type'))
    LOCAL_ROOT: str = Field("frontend/blogs", validation_alias=AliasChoices('LOCAL_ROOT', 'local_root'))

class ContentAPISettings(BaseModel):
    TAVILY_API_KEY: str
    GUARDIAN_API_KEY: str
    UNSPLASH_API_KEY: str

class Settings(BaseSettings):
    llm: LLMSettings
    tags: TagSettings = Field(default_factory=TagSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    r2: Optional[R2Settings] = None
    content: ContentAPISettings

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore"
    )

app_settings = Settings()