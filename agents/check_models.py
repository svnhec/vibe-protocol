import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

print("🔍 Checking available Google AI models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ Content Gen: {m.name}")
        if 'embedContent' in m.supported_generation_methods:
            print(f"🔹 Embedding:   {m.name}")
except Exception as e:
    print(f"❌ Error listing models: {e}")

