import requests
import re
import asyncio
import time
from telethon import TelegramClient, events

# === SOLANA RPC URL ===
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

# === TELEGRAM API CREDENTIALS ===
api_id = 25903302
api_hash = '6c2358b0acd76bb7bfaf9c2acd260127'
phone_number = '+918979351556'

# === GROUP IDS ===
main_group_id = -1002404342613 # Main group where tokens are announced
trojan_bot_username = '@solana_trojanbot'  # Trojan bot username
third_group_id = -4794132629  # Group where the confirmation message is sent (@shazhusain)

# === DEXSCREENER API ===
DEXSCREENER_API_URL = 'https://api.dexscreener.com/latest/dex/search'

# === INITIALIZE TELEGRAM CLIENT ===
client = TelegramClient('session_name', api_id, api_hash)

# === TRACK BOUGHT TOKENS ===
bought_coins = set()  # Use a set for O(1) lookup time

# === COINS TO AVOID (Lowercase for Fast Lookups) ===
avoid_coins = {"fwog", "alpha","vine","miggles","trump","Melania","butthole","fartcoin","Benji","botify"}  # Coins we don't want to buy

async def fetch_token_data(symbol):
    """Fetch contract address, ensuring liquidity and volume requirements are met."""
    url = f"{DEXSCREENER_API_URL}?q={symbol}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            for pair in response.json().get('pairs', []):
                liquidity = pair.get('liquidity', {}).get('usd', 0)
                volume_24h = pair.get('volume', {}).get('h24', 0)
                if pair['chainId'] == 'solana' and liquidity >= 100000 and volume_24h >= 10000:
                    return pair['baseToken']['address'], pair['baseToken']['name']
    except Exception as e:
        print(f"❌ Error fetching {symbol}: {e}")
    return None, None

async def click_sol_and_forward(symbol, contract_address):
    """Clicks 'SOL ✏️' and sends message immediately after success."""
    try:
        print(f"📩 Sending contract: {contract_address}")
        await client.send_message(trojan_bot_username, contract_address)

        retries = 5  # Number of retry attempts if button doesn't click
        clicked = False  # Flag to check if the button has been clicked

        # Retry loop for 5 attempts
        for _ in range(retries):
            async for message in client.iter_messages(trojan_bot_username, limit=3):
                if message.buttons:
                    for row in message.buttons:
                        for button in row:
                            if "SOL ✏️" in button.text:
                                await button.click()
                                clicked = True
                                print(f"✅ Clicked 'SOL ✏️' for {symbol}")
                                # Send message from the third group immediately after the click
                                async for message in client.iter_messages(third_group_id, limit=1):
                                    latest_message = message.text
                                    if latest_message:
                                        print(f"📤 Forwarding message: {latest_message}")
                                        await client.send_message(trojan_bot_username, latest_message)
                                return  # Exit after successful click and forwarding message

            # Retry if button is not found
            if not clicked:
                print(f"🔄 Retrying SOL ✏️ click for {symbol}...")
                await asyncio.sleep(0.5)

        print(f"❌ Failed to click SOL ✏️ after {retries} attempts for {symbol}")

    except Exception as e:
        print(f"❌ Error clicking SOL or sending message for {symbol}: {e}")

@client.on(events.NewMessage)
async def handle_new_message(event):
    """Processes new messages from the main group."""
    if event.chat_id != main_group_id:
        return

    message = event.message.text
    print(f"📥 Message received: {message}")

    # Extract symbols prefixed with `$` and numbers (including decimals)
    coin_symbols = {s.lower() for s in re.findall(r'\$(\w+)', message) if not s[0].isdigit()}
    numbers = {s for s in re.findall(r'\b\d+(\.\d+)?\b', message)}  # Capturing numbers with decimals

    # **Skip if any excluded coin is found**
    if avoid_coins & coin_symbols:
        print(f"⛔ Excluded coins detected: {avoid_coins & coin_symbols}")
        return  

    # **Skip already bought tokens**
    coin_symbols -= bought_coins  

    if not coin_symbols and not numbers:
        print("🔄 No new tokens or numbers to process.")
        return

    # **Fetch contracts in parallel for coins**
    tasks = [fetch_token_data(symbol) for symbol in coin_symbols]
    results = await asyncio.gather(*tasks)

    for symbol, (contract, token_name) in zip(coin_symbols, results):
        if contract:
            bought_coins.add(symbol)
            await click_sol_and_forward(symbol, contract)
        else:
            print(f"❌ Skipping {symbol}, contract not found.")

    # **Handle numbers if present**
    if numbers:
        for number in numbers:
            print(f"📤 Sending number: {number}")
            await client.send_message(trojan_bot_username, number)

async def main():
    """Starts Telegram client and monitoring."""
    await client.start(phone_number)
    print(f"👀 Monitoring main group: {main_group_id}")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())