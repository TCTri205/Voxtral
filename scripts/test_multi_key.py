import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to sys.path
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from llm_evaluator.llm_caller import LLMCaller

async def test_multi_key():
    load_dotenv()
    print("--- Multi-Key Handling Test (Safe Mode) ---")
    
    # 1. Check environment variables
    # We read but don't print the keys to avoid exposure.
    original_groq_keys = os.getenv("GROQ_API_KEYS") or os.getenv("GROQ_API_KEY") or ""
    
    # Simulate multiple keys if only one is found for testing purposes
    mock_key = "gsk_dummy_rotation_test_key_abc123"
    if original_groq_keys:
        test_keys_str = f"{original_groq_keys},{mock_key}"
    else:
        test_keys_str = f"gsk_real_key_placeholder,{mock_key}"
    
    # Explicitly set the environment variable for this process
    os.environ["GROQ_API_KEYS"] = test_keys_str
    
    groq_keys = [k.strip() for k in test_keys_str.split(",") if k.strip()]
    
    print(f"[ENV] Simulated {len(groq_keys)} Groq API keys (1 real, 1 mock).")
    
    if len(groq_keys) == 0:
        print("ERROR: No Groq API keys found in .env. Please set GROQ_API_KEYS (comma-separated).")
        return

    # 2. Check mask (last 4 chars) to confirm they are distinct
    for i, key in enumerate(groq_keys):
        mask = "*" * (len(key) - 4) + key[-4:] if len(key) > 4 else "****"
        print(f"  Key {i+1}: {mask}")

    # 3. Initialize LLMCaller
    print("\n[LLMCaller] Initializing...")
    caller = LLMCaller()
    
    # Count Groq clients
    groq_clients = [c for c in caller.clients if c["provider"] == "Groq"]
    print(f"[LLMCaller] Internal client count for Groq: {len(groq_clients)}")
    
    if len(groq_clients) != len(groq_keys):
        print(f"WARNING: Client count ({len(groq_clients)}) does not match key count ({len(groq_keys)})!")
    else:
        print("SUCCESS: Client count matches key count.")

    # 4. Test Rotation/Selection Logic
    print("\n[Selection] Testing strict round-robin selection logic...")
    selections = []
    # Test 10 times to see the sequence
    for i in range(10):
        client_info = caller.get_client_info(model="llama-3.3-70b-versatile")
        client_id = id(client_info["client"])
        selections.append(client_id)
        # Identify the key (safely)
        key_val = client_info["client"].api_key
        mask = "*" * (len(key_val) - 4) + key_val[-4:] if len(key_val) > 4 else "****"
        print(f"  Call {i+1}: Picked client with key ending in {mask} (ID: {client_id})")
    
    unique_clients_picked = set(selections)
    print(f"[Selection] Unique clients selected: {len(unique_clients_picked)}")
    
    if len(groq_clients) >= 2:
        # Check for alternation
        is_alternating = True
        for i in range(len(selections) - 1):
            if selections[i] == selections[i+1]:
                is_alternating = False
                break
        
        if is_alternating:
            print("SUCCESS: Selection is strictly alternating (round-robin).")
        else:
            print("FAILURE: Selection is NOT alternating! (Check if keys are unique or logic is sticky)")
    else:
        print(f"INFO: Only {len(groq_clients)} total Groq clients available. Alternation test skipped.")

if __name__ == "__main__":
    asyncio.run(test_multi_key())
