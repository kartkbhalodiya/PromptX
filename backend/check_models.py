"""Check available Gemini models"""
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    print("ERROR: GEMINI_API_KEY not found in .env")
    exit(1)

print("Connecting to Gemini API...")
client = genai.Client(api_key=api_key)

print("\n" + "="*60)
print("AVAILABLE GEMINI MODELS")
print("="*60 + "\n")

try:
    models = client.models.list()
    
    print(f"Total models found: {len(list(models))}\n")
    
    models = client.models.list()  # Re-fetch since we consumed the iterator
    
    for i, model in enumerate(models, 1):
        print(f"{i}. Model Name: {model.name}")
        if hasattr(model, 'display_name'):
            print(f"   Display Name: {model.display_name}")
        if hasattr(model, 'description'):
            desc = model.description[:80] if model.description else 'N/A'
            print(f"   Description: {desc}")
        if hasattr(model, 'supported_generation_methods'):
            print(f"   Methods: {', '.join(model.supported_generation_methods)}")
        print()
            
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
