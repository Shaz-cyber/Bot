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
main_group_id = -1002404342613 # Main group where tokens are announced
trojan_bot_username = '@solana_trojanbot'  # Trojan bot username
third_group_id = -4794132629  # Group where the confirmation message is sent (@shazhusain)

# === DEXSCREENER API ===
DEXSCREENER_API_URL = 'https://api.dexscreener.com/latest/dex/search'

# === INITIALIZE TELEGRAM CLIENT ===
client = TelegramClient('session_name', api_id, api_hash)

# === TRACK BOUGHT TOKENS ===
bought_coins = {}  # Track bought tokens by name and contract address

# === COINS TO AVOID ===
avoid_coins = {"fwog", "alpha","vine","miggles","trump","Melania","butthole","fartcoin","Benji","botify"}  # Coins we don't want to buy

async def fetch_token_data(symbol):
    """Fetch the contract address of a token if it meets liquidity and volume criteria."""
    url = f"{DEXSCREENER_API_URL}?q={symbol}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json().get('pairs', [])
            for pair in data:
                liquidity = pair.get('liquidity', {}).get('usd', 0)
                volume_24h = pair.get('volume', {}).get('h24', 0)  # Fetch 24-hour volume
                
                # Ensure the token is on Solana and meets both liquidity and volume requirements
                if pair['chainId'] == 'solana' and liquidity >= 100000 and volume_24h >= 10000:
                    print(f"✅ {symbol}: Liquidity = ${liquidity}, 24h Volume = ${volume_24h} (PASS)")
                    return pair['baseToken']['address'], pair['baseToken']['name']  # Return both address and name
                else:
                    print(f"❌ {symbol}: Liquidity = ${liquidity}, 24h Volume = ${volume_24h} (FAIL)")
    except Exception as e:
        print(f"❌ Error fetching contract for {symbol}: {e}")
    
    return None, None

def extract_solana_address(text):
    """Extracts Solana contract address from the message."""
    match = re.search(r'\b[A-Za-z0-9]{32,44}\b', text)  # Solana addresses are typically 32 to 44 characters long
    return match.group() if match else None

async def click_sol_and_forward(symbol, contract_address):
    """Click 'SOL ✏️' and forward number from third group."""
    try:
        print(f"📩 Sending contract for {symbol}: {contract_address}")
        await client.send_message(trojan_bot_username, contract_address)

        # **Look for the 'SOL ✏️' Button Quickly with Retries**
        for attempt in range(5):  # Retry up to 5 times
            async for message in client.iter_messages(trojan_bot_username, limit=3):
                if message.buttons:
                    for row in message.buttons:
                        for button in row:
                            if "SOL ✏️" in button.text:
                                print(f"✅ Found 'SOL ✏️' for {symbol}, clicking...")
                                await button.click()
                                break
                        else:
                            continue
                        break
                    else:
                        continue
                    break
                await asyncio.sleep(1)  # 1-second retry delay between attempts

            else:
                print(f"❌ 'SOL ✏️' button not found after {attempt + 1} attempts for {symbol}")
                continue
            break

        # **Fetch the Latest Numeric Message from Third Group (Whole & Decimal Numbers)**
        async for response_message in client.iter_messages(third_group_id, limit=5):
            match = re.search(r'\b\d+(\.\d+)?\b', response_message.text)  # Match whole & decimal numbers
            if match:
                number_to_forward = match.group()
                print(f"📨 Forwarding number {number_to_forward} to Trojan bot...")
                await client.send_message(trojan_bot_username, number_to_forward)
                print(f"✅ Successfully forwarded {number_to_forward} for {symbol}")
                return

        print("❌ No valid number found in third group!")

    except Exception as e:
        print(f"❌ Error clicking 'SOL ✏️' or forwarding for {symbol}: {e}")


@client.on(events.NewMessage)
async def handle_new_message(event):
    """Monitors the main group for token symbols and contract addresses."""
    if event.chat_id != main_group_id:
        return

    message = event.message.text
    print(f"📥 New message detected: {message}")

    # Extract token symbol (e.g., $alpha)
    coin_symbols = [s for s in re.findall(r'\$(\w+)', message) if not s[0].isdigit()]

    # Extract contract address
    contract_address = extract_solana_address(message)

    # Check if coin has already been bought (by name)
    def is_coin_bought_by_name(token_name):
        """Check if the coin has already been bought by name."""
        if token_name in bought_coins:
            print(f"🔄 Skipping {token_name}, already processed.")
            return True
        return False

    if contract_address:
        # If contract address is found, prioritize it
        token_name = None
        for symbol in coin_symbols:
            # Fetch token data (contract address and token name)
            ca, name = await fetch_token_data(symbol)

            if ca == contract_address:
                token_name = name
                break
        
        if token_name and not is_coin_bought_by_name(token_name) and token_name.lower() not in avoid_coins:
            # Mark as bought by token name and CA
            bought_coins[token_name] = contract_address
            print(f"💰 Bought {token_name} with contract {contract_address}")
            await click_sol_and_forward(token_name, contract_address)
        else:
            print(f"❌ Skipping {token_name} (either already bought or in the avoid list).")
        # Wait for a moment before checking the $ symbol (to ensure CA is processed)
        await asyncio.sleep(2)  # Delay to allow the bought coin to be added

    else:
        # If no contract address, proceed with symbol
        for symbol in coin_symbols:
            token_name = symbol.lower()

            if is_coin_bought_by_name(token_name) or token_name in avoid_coins:
                continue

            # Fetch token data from Dexscreener API for the $ symbol
            contract_address, token_name = await fetch_token_data(symbol)

            if contract_address:
                print(f"💰 Processing {symbol} with contract {contract_address}")
                # Check if this coin is already bought with CA (to avoid duplicate purchases)
                if is_coin_bought_by_name(token_name):
                    print(f"🔄 Skipping {symbol}, already processed by CA.")
                else:
                    bought_coins[token_name] = contract_address  # Mark as bought by token name and CA
                    await click_sol_and_forward(symbol, contract_address)
            else:
                print(f"❌ Skipping {symbol}, contract not found or insufficient liquidity/volume.")

async def main():
    """Starts the Telegram client and begins monitoring."""
    await client.start(phone_number)
    print(f"👀 Monitoring main group: {main_group_id}")
    await client.run_until_disconnected()


if __name__ == '__main__':
    asyncio.run(main())