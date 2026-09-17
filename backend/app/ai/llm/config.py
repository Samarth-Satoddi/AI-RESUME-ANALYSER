from pydantic import BaseModel, Field
from app.core.config import settings


class LLMConfig(BaseModel):
    model_name: str = Field(default_factory=lambda: settings.HF_MODEL_NAME)
    device: str = Field(default_factory=lambda: settings.HF_DEVICE)
    max_new_tokens: int = Field(default_factory=lambda: settings.HF_MAX_NEW_TOKENS)
    temperature: float = Field(default_factory=lambda: settings.HF_TEMPERATURE)
    top_p: float = Field(default_factory=lambda: settings.HF_TOP_P)
    torch_dtype: str = Field(default_factory=lambda: settings.HF_TORCH_DTYPE)
    load_in_4bit: bool = Field(default_factory=lambda: settings.HF_LOAD_IN_4BIT)
