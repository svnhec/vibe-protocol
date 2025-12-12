import os
import json
import requests
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime, timedelta
import google.generativeai as genai

load_dotenv()

# Configuration - Strip whitespace to avoid GitHub Secrets issues
PERPLEXITY_API_KEY = (os.getenv("PERPLEXITY_API_KEY") or "").strip()
GOOGLE_API_KEY = (os.getenv("GOOGLE_API_KEY") or "").strip()
SUPABASE_URL = (os.getenv("NEXT_PUBLIC_SUPABASE_URL") or "").strip()
SUPABASE_KEY = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()

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
    Identify 7 currently trending, controversial, or viral topics from TODAY across these categories:
    1. Pop Culture / Celebrities
    2. Tech / AI
    3. Crypto / Web3
    4. Global News / Politics
    5. Sports (NBA, NFL, Soccer, etc.)
    6. Science / Space
    7. Finance / Stocks / Economy

    Convert each into a specific, binary YES/NO betting market question with a clear resolution date.
    
    Return ONLY a JSON array with this structure:
    [
      {
        "question": "Will [Specific Event] happen by [Specific Date]?",
        "category": "Sports",
        "resolution_source": "http://espn.com or relevant site",
        "days_until_expiration": 3
      }
    ]
    Make questions SPECIFIC (include names, numbers, dates). Avoid vague terms like "major" or "significant".
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

        saved_count = 0
        for m in markets:
            try:
                if process_market(m):
                    saved_count += 1
            except Exception as e:
                print(f"⚠️ Failed to process market: {e}")
        
        print(f"🎉 Saved {saved_count} new markets!")

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
            return False

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

    # 3. DEDUPLICATION (Temporarily disabled - RPC has issues)
    # TODO: Fix vector RPC call format
    # For now, we skip this check and rely on the Critic to reject similar topics

    # 4. SAVE TO DB
    days = market_data.get("days_until_expiration", 7)
    expiration = (datetime.utcnow() + timedelta(days=days)).isoformat()

    # Category Images (Expanded)
    category_images = {
        "Pop Culture": "https://images.unsplash.com/photo-1514525253440-b393452e8d26?auto=format&fit=crop&w=1000",
        "Celebrities": "https://images.unsplash.com/photo-1514525253440-b393452e8d26?auto=format&fit=crop&w=1000",
        "Tech": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1000",
        "AI": "https://images.unsplash.com/photo-1677442135136-760c813028c4?auto=format&fit=crop&w=1000",
        "Crypto": "https://images.unsplash.com/photo-1518546305927-5a555bb7020d?auto=format&fit=crop&w=1000",
        "Web3": "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?auto=format&fit=crop&w=1000",
        "Global News": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1000",
        "Politics": "https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?auto=format&fit=crop&w=1000",
        "Sports": "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?auto=format&fit=crop&w=1000",
        "NBA": "https://images.unsplash.com/photo-1546519638-68e109498ffc?auto=format&fit=crop&w=1000",
        "NFL": "https://images.unsplash.com/photo-1566577739112-5180d4bf9390?auto=format&fit=crop&w=1000",
        "Soccer": "https://images.unsplash.com/photo-1574629810360-7efbbe195018?auto=format&fit=crop&w=1000",
        "Science": "https://images.unsplash.com/photo-1507413245164-6160d8298b31?auto=format&fit=crop&w=1000",
        "Space": "https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?auto=format&fit=crop&w=1000",
        "Finance": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1000",
        "Stocks": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1000",
        "Economy": "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?auto=format&fit=crop&w=1000"
    }
    cat = market_data["category"]
    
    # Smart matching: find key in category name
    image_url = category_images.get("Global News")  # Default
    for key in category_images:
        if key.lower() in cat.lower():
            image_url = category_images[key]
            break

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
    return True

if __name__ == "__main__":
    generate_markets()
