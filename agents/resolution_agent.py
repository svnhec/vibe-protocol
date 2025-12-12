import os
import json
import requests
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

# Configuration
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
WEB3_PROVIDER_URI = os.getenv("WEB3_PROVIDER_URI")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

# Initialize Web3
w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URI))

def resolve_market(question, market_id):
    """
    Analyzes a market question using Perplexity Online API.
    """
    print(f"🤖 Analyzing Market #{market_id}: '{question}'...")

    url = "https://api.perplexity.ai/chat/completions"

    payload = {
        "model": "sonar-pro",
        "messages": [
            {
                "role": "system",
                "content": "You are an impartial judge for a prediction market. You must determine if an event occurred based on real-time search results. Output ONLY valid JSON."
            },
            {
                "role": "user",
                "content": f"""
                Question: "{question}"
                
                Has this event happened? Search the web for the latest confirmation.
                
                Return a JSON object with:
                - "outcome": "YES", "NO", or "UNCERTAIN"
                - "confidence": A number between 0 and 100
                - "reasoning": A brief explanation of the evidence found.
                """
            }
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
            print(f"❌ Perplexity API Error: {data['error']}")
            return

        # Parse the content from Perplexity
        content = data['choices'][0]['message']['content']
        
        # Clean up code blocks if Perplexity adds them
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        result = json.loads(content)
        print(f"🤔 AI Analysis: {result}")

        # Execute Resolution if confident
        if result["outcome"] != "UNCERTAIN" and result["confidence"] > 95:
            execute_on_chain(market_id, result["outcome"] == "YES")
        else:
            print("⚠️ Outcome uncertain or low confidence. Manual review required.")
            
    except Exception as e:
        print(f"Error calling Perplexity: {e}")

def execute_on_chain(market_id, outcome_bool):
    """
    Calls the resolveMarket function on the smart contract.
    """
    print(f"⚡ Executing On-Chain Resolution for Market {market_id} -> {outcome_bool}")
    
    contract_abi = [
        {
            "inputs": [
                {"internalType": "uint256", "name": "marketId", "type": "uint256"},
                {"internalType": "bool", "name": "outcome", "type": "bool"}
            ],
            "name": "resolveMarket",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function"
        }
    ]
    
    contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)
    
    # Build Transaction
    account = w3.eth.account.from_key(PRIVATE_KEY)
    nonce = w3.eth.get_transaction_count(account.address)
    
    tx = contract.functions.resolveMarket(market_id, outcome_bool).build_transaction({
        'chainId': 84532, # Base Sepolia
        'gas': 200000,
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce,
    })
    
    # Sign and Send
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    
    print(f"✅ Transaction Sent! Hash: {w3.to_hex(tx_hash)}")

# Example Usage
if __name__ == "__main__":
    resolve_market("Did Taylor Swift announce a tour date today?", 123)
