import os
import json
import requests
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime, timedelta
import google.generativeai as genai

load_dotenv()

# Configuration
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") # User needs to add this
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_KEY:
    print("❌ Error: SUPABASE_SERVICE_ROLE_KEY is missing in .env")
    exit(1)

if not GOOGLE_API_KEY:
    print("❌ Error: GOOGLE_API_KEY is missing in .env")
    exit(1)

# Configure Google AI
genai.configure(api_key=GOOGLE_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def generate_markets():
    print("🤖 Trend Bot V2 (Gemini Edition): Scanning & Critiquing...")

    url = "https://api.perplexity.ai/chat/completions"
    
    prompt = """
    Identify 3 currently trending, controversial, or viral topics (1 Pop Culture, 1 Tech/Crypto, 1 Global News) from TODAY.
    Convert each into a binary YES/NO betting market question.
    
    Return ONLY a JSON array with this structure:
    [
      {
        "question": "Will [Event] happen by [Date]?",
        "category": "Pop Culture",
        "resolution_source": "http://example.com",
        "days_until_expiration": 3
      }
    ]
    """

    payload = {
        "model": "sonar-pro",
        "messages": [
            { "role": "system", "content": "You are a market maker. Output valid JSON only." },
            { "role": "user", "content": prompt }
        ]
    }

    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        
        if 'error' in data:
            print(f"❌ Perplexity Error: {data['error']}")
            return

        content = data['choices'][0]['message']['content']
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        markets = json.loads(content)
        print(f"✨ AI found {len(markets)} candidates. Running Gemini Critic...")

        for m in markets:
            process_market(m)

    except Exception as e:
        print(f"Error generating markets: {e}")

def process_market(market_data):
    question = market_data["question"]
    
    # 1. THE CRITIC (Gemini)
    critic_prompt = f"""
    Evaluate this betting market question for clarity, objective resolvability, and safety (No violence/death).
    Question: "{question}"
    
    Return ONLY a JSON object:
    {{
        "score": (0-100),
        "reason": "explanation"
    }}
    """
    
    # Switch to 'gemini-2.5-flash'
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(critic_prompt)
    
    try:
        text = response.text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
            
        critic_result = json.loads(text)
        
        if critic_result["score"] < 85:
            print(f"🛑 REJECTED ({critic_result['score']}): {question} - {critic_result['reason']}")
            return

        print(f"✅ APPROVED ({critic_result['score']}): {question}")
    except Exception as e:
        print(f"⚠️ Critic Error (skipping validation): {e}")

    # 2. GENERATE EMBEDDING (Gemini)
    vector_input = f"{market_data['category']}: {question}"
    
    embedding_result = genai.embed_content(
        model="models/text-embedding-004",
        content=vector_input,
        task_type="retrieval_document"
    )
    embedding = embedding_result['embedding']

    # 3. CHECK FOR DUPLICATES
    # We ask DB: "Is there anything 85% similar to this?"
    try:
        response = supabase.rpc("check_duplicate_market", {
            "new_embedding": embedding, 
            "match_threshold": 0.85
        }).execute()
        
        # Supabase-py v2 returns data in .data
        if response.data is True:
            print(f"🛑 DUPLICATE DETECTED: {question}")
            return
    except Exception as e:
        print(f"⚠️ Deduplication check failed: {e}")

    # 4. SAVE TO DB
    days = market_data.get("days_until_expiration", 7)
    expiration = (datetime.utcnow() + timedelta(days=days)).isoformat()

    # Placeholders
    category_images = {
        "Pop Culture": "https://images.unsplash.com/photo-1514525253440-b393452e8d26?auto=format&fit=crop&w=1000",
        "Tech": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1000",
        "Crypto": "https://images.unsplash.com/photo-1518546305927-5a555bb7020d?auto=format&fit=crop&w=1000",
        "Global News": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1000"
    }
    cat = market_data["category"]
    image_url = category_images.get(cat, category_images["Global News"])
    if "Crypto" in cat: image_url = category_images["Crypto"]
    if "Tech" in cat: image_url = category_images["Tech"]

    new_market = {
        "question": question,
        "category": cat,
        "image_url": image_url,
        "resolution_source": market_data["resolution_source"],
        "expiration_date": expiration,
        "status": "OPEN",
        "outcomes": {"yes": 0.5, "no": 0.5},
        "embedding": embedding 
    }
    
    supabase.table("markets").insert(new_market).execute()
    print(f"💾 Saved with Vector!")

if __name__ == "__main__":
    generate_markets()
