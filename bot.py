import requests
import re
import asyncio
from telethon import TelegramClient, events

# === SOLANA RPC URL ===
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

# === TELEGRAM API CREDENTIALS ===
api_id = 25903302
api_hash = '6c2358b0acd76bb7bfaf9c2acd260127'
phone_number = '+918979351556'

# === GROUP IDS ===
main_group_id = -1002404342613  # Main group ID
trojan_bot_username = '@solana_trojanbot'  # Trojan bot username
third_group_id = -4794132629  # Confirmation group (@shazhusain)

# === DEXSCREENER API ===
DEXSCREENER_API_URL = 'https://api.dexscreener.com/latest/dex/search'

# === INITIALIZE TELEGRAM CLIENT ===
client = TelegramClient('session_name', api_id, api_hash)

# === TRACK BOUGHT TOKENS ===
bought_tokens = {}  # Track bought tokens {contract: ticker, ticker: contract}

# === COINS TO AVOID (Lowercase for Fast Lookups) ===
avoid_coins = {"fwog", "alpha", "vine", "miggles", "trump", "melania", "butthole", "fartcoin", "benji", "botify"}

async def fetch_token_data(symbol):
    """Fetch contract address ensuring liquidity and volume requirements."""
    url = f"{DEXSCREENER_API_URL}?q={symbol}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            for pair in response.json().get('pairs', []):
                liquidity = pair.get('liquidity', {}).get('usd', 0)
                volume_24h = pair.get('volume', {}).get('h24', 0)
                if pair['chainId'] == 'solana' and liquidity >= 100000 and volume_24h >= 10000:
                    return pair['baseToken']['address'], pair['baseToken']['symbol']
    except Exception as e:
        print(f"❌ Error fetching {symbol}: {e}")
    return None, None

async def click_sol_and_forward(contract_address, token_ticker):
    """Buys token using Trojan bot and forwards confirmation."""
    if contract_address in bought_tokens:
        print(f"❌ Already bought with CA: {contract_address}")
        return
    
    await client.send_message(trojan_bot_username, "/buy")
    await asyncio.sleep(0.3)  # Ensure correct message order
    await client.send_message(trojan_bot_username, contract_address)
    
    retries = 5
    for _ in range(retries):
        async for message in client.iter_messages(trojan_bot_username, limit=3):
            if message.buttons:
                for row in message.buttons:
                    for button in row:
                        if "SOL ✏" in button.text:
                            await button.click()
                            print(f"✅ Clicked 'SOL ✏' button for CA: {contract_address}")
                            async for msg in client.iter_messages(third_group_id, limit=1):
                                if msg.text.isdigit():
                                    await client.send_message(trojan_bot_username, msg.text)
                                    bought_tokens[contract_address] = token_ticker.lower()
                                    bought_tokens[token_ticker.lower()] = contract_address
                                    return
        await asyncio.sleep(0.3)
    print(f"❌ Failed to click 'SOL ✏' after {retries} attempts for CA: {contract_address}")

@client.on(events.NewMessage)
async def handle_new_message(event):
    """Processes new messages from the main group."""
    if event.chat_id != main_group_id:
        return
    
    message = event.message.text
    print(f"📥 Message received: {message}")
    
    contract_match = re.search(r'([1-9A-HJ-NP-Za-km-z]{32,44})', message)
    coin_symbols = {s.lower() for s in re.findall(r'\$(\w+)', message) if not s[0].isdigit()}
    
    if contract_match:
        contract_address = contract_match.group(1)
        if contract_address in bought_tokens:
            print(f"❌ Already bought with CA: {contract_address}")
            return
        await click_sol_and_forward(contract_address, "Unknown")
        return
    
    if avoid_coins & coin_symbols:
        print(f"⛔ Excluded coins detected: {avoid_coins & coin_symbols}")
        return  
    
    coin_symbols -= set(bought_tokens.keys())
    if not coin_symbols:
        print("🔄 No new tokens to process.")
        return
    
    tasks = [fetch_token_data(symbol) for symbol in coin_symbols]
    results = await asyncio.gather(*tasks)
    
    for symbol, (contract, token_ticker) in zip(coin_symbols, results):
        if contract:
            if contract in bought_tokens:
                print(f"❌ Already bought {token_ticker} with CA: {contract}")
                continue
            await click_sol_and_forward(contract, token_ticker)
        else:
            print(f"⚠️ {symbol} not found on DexScreener, skipping purchase due to liquidity/volume filter.")

async def main():
    await client.start(phone_number)
    print(f"👀 Monitoring main group: {main_group_id}")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())