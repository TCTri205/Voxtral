import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to sys.path
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from llm_evaluator.llm_caller import LLMCaller
from llm_evaluator.schema import EvaluationCandidate

async def test_api():
    load_dotenv()
    print("--- API Connection Test ---")
    
    # 1. Check if keys are loaded
    openai_keys = os.getenv("OPENAI_API_KEYS") or os.getenv("OPENAI_API_KEY") or ""
    groq_keys = os.getenv("GROQ_API_KEYS") or os.getenv("GROQ_API_KEY") or ""
    
    if not openai_keys and not groq_keys:
        print("Error: No API keys (OpenAI or Groq) found in .env")
        return

    print(f"Found configuration (OpenAI: {'Yes' if openai_keys else 'No'}, Groq: {'Yes' if groq_keys else 'No'})")
    print(f"Initializing LLMCaller...")
    
    try:
        caller = LLMCaller()
        # Create a dummy candidate for a tiny test
        candidate = EvaluationCandidate(
            filename="test_audio.mp3",
            canonical_id="test_audio",
            hyp_transcript="Hello, how are you?",
            gt_plain="Hello, how are you?"
        )
        
        # Focused on Groq as the primary provider
        models_to_test = []
        if groq_keys:
            models_to_test.append(("llama-3.3-70b-versatile", "Groq"))
        else:
            print("WARNING: Groq keys not found!")
            print("WARNING: Groq keys not found for testing.")

        for model, provider in models_to_test:
            print(f"\nSending a test request to {provider} ({model})...")
            result = await caller.evaluate_single(candidate, model=model)
            
            if "failed" in result.reasoning.lower():
                print(f"FAILED {provider}: {result.reasoning}")
            else:
                print(f"SUCCESS {provider}! API responded correctly.")
                print(f"Reasoning: {result.reasoning}")
            
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_api())
