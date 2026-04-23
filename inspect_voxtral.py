import sys
import torch
from transformers import AutoProcessor, AutoConfig

model_id = "mistralai/Voxtral-Mini-4B-Realtime-2602"
print(f"Loading config and processor for {model_id}...")

try:
    config = AutoConfig.from_pretrained(model_id, trust_remote_code=True)
    print("CONFIG KEYS:")
    print(list(config.__dict__.keys()))
    if hasattr(config, "condition_on_previous_text"):
        print("HAS condition_on_previous_text:", config.condition_on_previous_text)
    if hasattr(config, "no_speech_threshold"):
        print("HAS no_speech_threshold:", config.no_speech_threshold)
    
except Exception as e:
    print("Error loading config:", e)

try:
    processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
    print("PROCESSOR class:", processor.__class__.__name__)
    print("Has get_decoder_prompt_ids:", hasattr(processor, "get_decoder_prompt_ids"))
except Exception as e:
    print("Error loading processor:", e)
