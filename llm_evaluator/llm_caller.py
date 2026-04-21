import asyncio
import os
import openai
import random
import json
from typing import List
from dotenv import load_dotenv
from .schema import EvaluationCandidate, EvaluationResult
from .prompt_builder import build_prompt

class LLMCaller:
    def __init__(self, api_keys: List[str] = None):
        self.clients = []
        load_dotenv()
        
        # 1. Load OpenAI Keys
        openai_keys_str = os.getenv("OPENAI_API_KEYS") or os.getenv("OPENAI_API_KEY") or ""
        openai_keys = [k.strip() for k in openai_keys_str.split(",") if k.strip()]
        for k in openai_keys:
            self.clients.append({
                "provider": "OpenAI",
                "client": openai.AsyncOpenAI(
                    api_key=k,
                    base_url=os.getenv("OPENAI_BASE_URL") or None # None uses the default openai base url
                )
            })
            
        # 2. Load Groq Keys
        groq_keys_str = os.getenv("GROQ_API_KEYS") or os.getenv("GROQ_API_KEY") or ""
        groq_keys = [k.strip() for k in groq_keys_str.split(",") if k.strip()]
        for k in groq_keys:
            self.clients.append({
                "provider": "Groq",
                "client": openai.AsyncOpenAI(
                    api_key=k,
                    base_url="https://api.groq.com/openai/v1"
                )
            })
            
        if not self.clients:
            raise ValueError("No API keys found. Please set OPENAI_API_KEY/OPENAI_API_KEYS or GROQ_API_KEY/GROQ_API_KEYS.")
        
        self._provider_indices = {}
        for c in self.clients:
            provider = c["provider"]
            if provider not in self._provider_indices:
                self._provider_indices[provider] = 0
        
        self._global_index = 0

    def get_client_info(self, model: str = None):
        """
        Selects an appropriate client based on the model name.
        If no specific model is provided or no specific match is found, uses round-robin.
        """
        # 1. Try to find a specific provider based on model prefix
        preferred_provider = None
        if model:
            if model.startswith("gpt-") or model.startswith("javis/"):
                preferred_provider = "OpenAI"
            elif any(m in model.lower() for m in ["llama", "mixtral", "deepseek", "gemma", "qwen", "gpt-oss"]):
                preferred_provider = "Groq"

        if preferred_provider:
            # Filter clients by provider
            matching_clients = [c for c in self.clients if c["provider"] == preferred_provider]
            if matching_clients:
                # Strict round-robin per provider
                idx = self._provider_indices[preferred_provider]
                client_info = matching_clients[idx % len(matching_clients)]
                self._provider_indices[preferred_provider] = (idx + 1) % len(matching_clients)
                return client_info

        # 2. Fallback: If we have an OpenAI client with a custom base URL, it might be a self-hosted model
        # Try to use OpenAI provider as a general fallback if available
        openai_clients = [c for c in self.clients if c["provider"] == "OpenAI"]
        if openai_clients:
            idx = self._provider_indices["OpenAI"]
            client_info = openai_clients[idx % len(openai_clients)]
            self._provider_indices["OpenAI"] = (idx + 1) % len(openai_clients)
            return client_info

        # 3. Fallback to global round-robin
        info = self.clients[self._global_index]
        self._global_index = (self._global_index + 1) % len(self.clients)
        return info

    def get_client(self, model: str = None):
        return self.get_client_info(model)["client"]

    async def evaluate_single(
        self, 
        candidate: EvaluationCandidate, 
        model: str = "llama-3.3-70b-versatile",
        max_retries: int = 3
    ) -> EvaluationResult:
        """Evaluates a single candidate with retries."""
        prompt = build_prompt(candidate)
        
        last_exception = None
        for attempt in range(max_retries):
            client_info = self.get_client_info(model=model)
            client = client_info["client"]
            provider = client_info["provider"]
            
            try:
                print(f"[LLMCaller] Attempt {attempt+1} using {provider} for model {model}")
                
                if provider == "OpenAI" and model.startswith("gpt-"):
                    # Use the native parse method (uses Structured Outputs) for official OpenAI models
                    response = await client.beta.chat.completions.parse(
                        model=model,
                        messages=[
                            {"role": "system", "content": prompt["system"]},
                            {"role": "user", "content": prompt["user"]}
                        ],
                        response_format=EvaluationResult,
                        temperature=0.0
                    )
                    result = response.choices[0].message.parsed
                else:
                    # For self-hosted (LiteLLM) or Groq, use local manual parsing
                    # Note: Structured Outputs (.parse) is often not supported on self-hosted endpoints
                    schema_json = json.dumps(EvaluationResult.model_json_schema(), indent=2)
                    response = await client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": prompt["system"] + f"\n\nIMPORTANT: Return ONLY a valid JSON object matching the following schema:\n{schema_json}"},
                            {"role": "user", "content": prompt["user"] + (f"\n\nPlease include 'filename': '{candidate.filename}' in your response." if candidate.filename else "")}
                        ],
                        response_format={"type": "json_object"} if provider == "Groq" or "litellm" in (os.getenv("OPENAI_BASE_URL") or "").lower() else None,
                        temperature=0.0
                    )
                    content = response.choices[0].message.content
                    result_data = json.loads(content)
                    
                    # Ensure filename is present before validation if model missed it
                    if "filename" not in result_data:
                        result_data["filename"] = candidate.filename
                        
                    result = EvaluationResult.model_validate(result_data)
                
                # Ensure filename and existing metrics are preserved
                result.filename = candidate.filename
                result.existing_cer = candidate.existing_cer
                result.existing_rf = candidate.existing_rf
                result.existing_inference_rtf = candidate.existing_inference_rtf
                
                return result
            except Exception as e:
                last_exception = e
                # Check for rate limit or transient error
                is_rate_limit = "429" in str(e)
                if is_rate_limit or attempt < max_retries - 1:
                    # Rotate client is done by self.get_client() in next iteration
                    wait_time = (attempt + 1) * 2
                    await asyncio.sleep(wait_time)
                    continue
                break
        
        # Fallback for failed API called after retries
        return EvaluationResult(
            filename=candidate.filename,
            has_hallucination=False,
            primary_error="none",
            reasoning=f"LLM call failed after {max_retries} attempts: {str(last_exception)}",
            review_status="manual_review",
            confidence="low",
            existing_cer=candidate.existing_cer,
            existing_rf=candidate.existing_rf,
            existing_inference_rtf=candidate.existing_inference_rtf
        )

    async def evaluate_batch(
        self, 
        candidates: List[EvaluationCandidate], 
        model: str = "llama-3.3-70b-versatile",
        concurrency: int = 5
    ) -> List[EvaluationResult]:
        """Evaluates a batch of candidates concurrently."""
        semaphore = asyncio.Semaphore(concurrency)
        
        async def sem_evaluate(c):
            async with semaphore:
                return await self.evaluate_single(c, model)
        
        tasks = [sem_evaluate(c) for c in candidates]
        return await asyncio.gather(*tasks)
