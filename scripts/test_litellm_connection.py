import asyncio
import os
from dotenv import load_dotenv
from llm_evaluator.llm_caller import LLMCaller
from llm_evaluator.schema import EvaluationCandidate

async def test_connection():
    load_dotenv()
    
    # Use the model provided by the user or fallback to a default
    model = os.getenv("EVALUATION_MODEL", "javis/Qwen3-14B-AWQ")
    base_url = os.getenv("OPENAI_BASE_URL")
    
    print(f"Testing connection to: {base_url}")
    print(f"Using model: {model}")
    
    caller = LLMCaller()
    
    # Mock candidate matching schema.py
    candidate = EvaluationCandidate(
        filename="test_file.wav",
        canonical_id="test_id",
        hyp_transcript="This is a test sentence.",
        gt_plain="This is a test sentence.",
        existing_cer="0.0",
        existing_rf=0,
        existing_inference_rtf=0.0
    )
    
    try:
        result = await caller.evaluate_single(candidate, model=model)
        print("\nSuccess! Response received:")
        print(f"Has Hallucination: {result.has_hallucination}")
        print(f"Reasoning: {result.reasoning}")
    except Exception as e:
        print(f"\nFailed to connect or get response: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
