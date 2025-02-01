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
main_group_id = -1002301815227  # Main group where tokens are announced
trojan_bot_username = '@solana_trojanbot'  # Trojan bot username
third_group_id = -4794132629  # Group where the confirmation message is sent (@shazhusain)

# === DEXSCREENER API ===
DEXSCREENER_API_URL = 'https://api.dexscreener.com/latest/dex/search'

# === INITIALIZE TELEGRAM CLIENT ===
client = TelegramClient('session_name', api_id, api_hash)

# === TRACK BOUGHT TOKENS ===
bought_coins = {"fwog","vine","miggles","alpha","benji","trump","melania","butthole","botify","fartcoin","jup","ray"}

async def fetch_solana_balance(wallet_address):
    """Fetch balance of the Solana wallet address."""
    try:
        response = requests.post(
            SOLANA_RPC_URL,
            json={"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [wallet_address]},
            headers={"Content-Type": "application/json"}
        )
        balance = response.json().get('result', {}).get('value', 0)
        return balance / 1e9  # Convert lamports to SOL
    except Exception as e:
        print(f"❌ Error fetching Solana balance: {e}")
        return None

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
                    return pair['baseToken']['address']
                else:
                    print(f"❌ {symbol}: Liquidity = ${liquidity}, 24h Volume = ${volume_24h} (FAIL)")
    except Exception as e:
        print(f"❌ Error fetching contract for {symbol}: {e}")
    
    return None

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
    """Monitors the main group for token symbols and interacts with Trojan Bot."""
    if event.chat_id != main_group_id:
        return

    message = event.message.text
    print(f"📥 New message detected: {message}")

    coin_symbols = [s for s in re.findall(r'\$(\w+)', message) if not s[0].isdigit()]

    for symbol in coin_symbols:
        if symbol in bought_coins:
            print(f"🔄 Skipping {symbol}, already processed.")
            continue

        # **Fetch Data in Parallel for Speed**
        contract_address, solana_balance = await asyncio.gather(
            fetch_token_data(symbol),
            fetch_solana_balance("CsUZFwXSkVkEaFKYfSLjCCatoTD9g986seP293oEHw5r")
        )

        if contract_address and solana_balance is not None:
            print(f"💰 Balance: {solana_balance} SOL | Processing {symbol}")
            bought_coins.add(symbol)
            await click_sol_and_forward(symbol, contract_address)
        else:
            print(f"❌ Skipping {symbol}, contract not found or insufficient balance.")


async def main():
    """Starts the Telegram client and begins monitoring."""
    await client.start(phone_number)
    print(f"👀 Monitoring main group: {main_group_id}")
    await client.run_until_disconnected()


if __name__ == '__main__':
    asyncio.run(main())
