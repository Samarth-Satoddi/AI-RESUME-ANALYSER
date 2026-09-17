import os
import sys
import threading
from typing import Optional, Any, Dict, List
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.ai.llm.config import LLMConfig


class LLMModelManager:
    """
    Thread-safe Singleton Model Manager for local LLM inference.
    Supports Hugging Face Transformers (AutoModelForCausalLM + AutoTokenizer)
    with GPU (CUDA) acceleration and CPU fallback, as well as local Ollama backend
    if the user's pre-downloaded local models are selected.
    """

    _instance: Optional["LLMModelManager"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: Optional[LLMConfig] = None):
        if hasattr(self, "_initialized") and self._initialized:
            return

        self.config = config or LLMConfig()
        self.model = None
        self.tokenizer = None
        self.device = "cpu"
        self.is_loaded = False
        self.load_error: Optional[str] = None
        self.backend_type = "transformers"  # 'transformers' or 'ollama'
        self._load_lock = threading.Lock()
        self._initialized = True

    def _check_ollama_model_available(self, model_name: str) -> bool:
        """Checks if local Ollama daemon is running and has the requested model."""
        try:
            resp = httpx.get("http://127.0.0.1:11434/api/tags", timeout=1.5)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "").lower() for m in data.get("models", [])]
                clean_target = model_name.lower()
                for m in models:
                    if m == clean_target or m.startswith(clean_target) or clean_target.startswith(m.split(":")[0]):
                        return True
        except Exception:
            pass
        return False

    def load_model(self) -> bool:
        """
        Loads the configured model into memory once.
        Ensures thread-safety and graceful failure logging.
        """
        with self._load_lock:
            if self.is_loaded:
                return True

            model_name = self.config.model_name
            logger.info(f"Initializing AI Assistant model: {model_name}")

            # Check if requested model is in local Ollama
            if self._check_ollama_model_available(model_name):
                self.backend_type = "ollama"
                self.device = "local-ollama (GPU accelerated)"
                self.is_loaded = True
                logger.info(f"Model loaded successfully via local Ollama engine: {model_name} (Device: {self.device})")
                return True

            # Otherwise, load via Hugging Face Transformers
            self.backend_type = "transformers"
            try:
                import torch
                from transformers import AutoModelForCausalLM, AutoTokenizer

                # Device detection
                if self.config.device == "cuda" or (self.config.device == "auto" and torch.cuda.is_available()):
                    self.device = "cuda"
                    device_map = "auto"
                    torch_dtype = torch.float16
                    gpu_name = torch.cuda.get_device_name(0)
                    logger.info(f"CUDA GPU detected: {gpu_name}. Loading model in float16.")
                else:
                    self.device = "cpu"
                    device_map = None
                    torch_dtype = torch.float32
                    logger.info("Using CPU for model inference.")

                logger.info(f"Loading Hugging Face Tokenizer: {model_name}")
                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_name,
                    trust_remote_code=True,
                )

                logger.info(f"Loading Hugging Face Model: {model_name} on device: {self.device}")
                if self.device == "cuda":
                    self.model = AutoModelForCausalLM.from_pretrained(
                        model_name,
                        torch_dtype=torch_dtype,
                        device_map=device_map,
                        trust_remote_code=True,
                    )
                else:
                    self.model = AutoModelForCausalLM.from_pretrained(
                        model_name,
                        torch_dtype=torch_dtype,
                        trust_remote_code=True,
                    )
                    self.model.to("cpu")

                self.is_loaded = True
                self.load_error = None
                logger.info(f"Model loaded successfully. Model: {model_name} | Device: {self.device} | Dtype: {torch_dtype}")
                return True

            except Exception as exc:
                err_msg = f"Failed to load Hugging Face model '{model_name}': {str(exc)}"
                logger.error(err_msg, exc_info=True)
                self.load_error = err_msg
                self.is_loaded = False
                return False

    def generate(self, messages: List[Dict[str, str]], max_new_tokens: Optional[int] = None, temperature: Optional[float] = None) -> str:
        """
        Executes generation using loaded model.
        """
        if not self.is_loaded:
            if not self.load_model():
                raise RuntimeError(self.load_error or "Model is not loaded.")

        max_tokens = max_new_tokens or self.config.max_new_tokens
        temp = temperature if temperature is not None else self.config.temperature

        if self.backend_type == "ollama":
            return self._generate_ollama(messages, max_tokens, temp)
        else:
            return self._generate_transformers(messages, max_tokens, temp)

    def _generate_ollama(self, messages: List[Dict[str, str]], max_tokens: int, temp: float) -> str:
        """Fast local generation using local Ollama daemon."""
        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temp,
                "top_p": self.config.top_p,
            }
        }
        resp = httpx.post("http://127.0.0.1:11434/api/chat", json=payload, timeout=60.0)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("message", {}).get("content", "").strip()
        raise RuntimeError(f"Ollama generation failed with status {resp.status_code}: {resp.text}")

    def _generate_transformers(self, messages: List[Dict[str, str]], max_tokens: int, temp: float) -> str:
        """Generation using Hugging Face Transformers pipeline."""
        import torch

        if not self.tokenizer or not self.model:
            raise RuntimeError("Model or tokenizer is not initialized.")

        # Apply chat template
        if hasattr(self.tokenizer, "apply_chat_template") and self.tokenizer.chat_template:
            prompt_text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        else:
            # Fallback formatting if chat template is absent
            formatted = []
            for m in messages:
                role = m.get("role", "user").capitalize()
                formatted.append(f"{role}: {m.get('content', '')}")
            formatted.append("Assistant:")
            prompt_text = "\n\n".join(formatted)

        inputs = self.tokenizer(prompt_text, return_tensors="pt")
        if self.device == "cuda":
            inputs = {k: v.to("cuda") for k, v in inputs.items()}

        gen_kwargs = {
            "max_new_tokens": max_tokens,
            "pad_token_id": self.tokenizer.eos_token_id,
        }
        if temp > 0.0:
            gen_kwargs["temperature"] = temp
            gen_kwargs["do_sample"] = True
            gen_kwargs["top_p"] = self.config.top_p
        else:
            gen_kwargs["do_sample"] = False

        with torch.no_grad():
            output_tokens = self.model.generate(
                **inputs,
                **gen_kwargs,
            )

        # Slice off the prompt tokens to get only generated tokens
        input_len = inputs["input_ids"].shape[1]
        new_tokens = output_tokens[0][input_len:]
        response = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        return response


_model_manager_instance: Optional[LLMModelManager] = None


def get_llm_manager() -> LLMModelManager:
    """Returns singleton LLM model manager."""
    global _model_manager_instance
    if _model_manager_instance is None:
        _model_manager_instance = LLMModelManager()
    return _model_manager_instance
