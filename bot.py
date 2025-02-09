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

# === INITIALIZE TELEGRAM CLIENT ===
client = TelegramClient('session_name', api_id, api_hash)

# === TRACK PURCHASED CONTRACT ADDRESSES (CAs) ===
bought_contracts = set()  # Stores purchased contract addresses

# === COINS TO AVOID (Now Using Contract Addresses) ===
excluded_contracts = {"2sCUCJdVkmyXp4dT8sFaA9LKgSMK4yDPi9zLHiwXpump","EgMF2iEbKv984fWtqakZ12k4VQvJubTNnU2Y9durpump","EsP4kJfKUDLfX274WoBSiiEy74Sh4tZKUCDjfULHpump"
   
}

async def fetch_latest_number_from_third_group():
    """Fetches the latest numerical message (integer or float) from the last 3 messages in the third group."""
    async for msg in client.iter_messages(third_group_id, limit=3):
        match = re.search(r'\b\d+(?:\.\d+)?\b', msg.text)
        if match:
            latest_number = match.group(0)  # Capture full number including decimals
            print(f"📨 Found latest numerical message: {latest_number}")
            return latest_number
    
    print("⚠ No valid numerical message found in the last 3 messages.")
    return None

async def is_sol_button_disappeared():
    """Checks if the 'SOL ✏' button has disappeared from Trojan bot chat."""
    async for msg in client.iter_messages(trojan_bot_username, limit=5):
        if msg.buttons:
            for row in msg.buttons:
                for button in row:
                    if "SOL ✏" in button.text:
                        print("⚠ 'SOL ✏' button is still visible, retrying...")
                        return False
    print("✅ 'SOL ✏' button has disappeared. Proceeding...")
    return True

async def click_sol_and_forward(contract_address):
    """Buys token using Trojan bot and ensures confirmation before proceeding."""
    if contract_address in bought_contracts or contract_address in excluded_contracts:
        print(f"❌ Already bought or excluded CA: {contract_address}")
        return
    
    await client.send_message(trojan_bot_username, "/buy")
    await asyncio.sleep(0.2)
    await client.send_message(trojan_bot_username, contract_address)

    retries = 10
    for _ in range(retries):
        async for message in client.iter_messages(trojan_bot_username, limit=3):
            if message.buttons:
                for row in message.buttons:
                    for button in row:
                        if "SOL ✏" in button.text:
                            await button.click()
                            print(f"✅ Clicked 'SOL ✏' for CA: {contract_address}")

                            # *Wait 1 second before forwarding number*
                            await asyncio.sleep(0.3)

                            # Fetch latest numerical message from the third group
                            number_msg = await fetch_latest_number_from_third_group()
                            if number_msg:
                                await client.send_message(trojan_bot_username, number_msg)
                                print(f"✅ Forwarded latest number {number_msg} to Trojan bot")

                                # *Check if 'SOL ✏' disappears before confirming*
                                for _ in range(10):  # Retry up to 10 times
                                    await asyncio.sleep(0.3)
                                    if await is_sol_button_disappeared():
                                        bought_contracts.add(contract_address)  # Save CA
                                        return

                                    # *If still visible, click again and resend number*
                                    await button.click()
                                    await asyncio.sleep(0.5)
                                    await client.send_message(trojan_bot_username, number_msg)
                                    print(f"🔄 Retried 'SOL ✏' click and resent number {number_msg}")

        await asyncio.sleep(0.2)
    
    print(f"❌ Failed to complete purchase after {retries} attempts for CA: {contract_address}")

@client.on(events.NewMessage)
async def handle_new_message(event):
    """Processes new messages from the main group."""
    if event.chat_id != main_group_id:
        return
    
    message = event.message.text.strip()
    print(f"📥 Message received: {message}")
    
    contract_match = re.search(r'([1-9A-HJ-NP-Za-km-z]{32,44})', message)

    if contract_match:
        contract_address = contract_match.group(1)

        if contract_address in bought_contracts or contract_address in excluded_contracts:
            print(f"❌ Already bought or excluded CA: {contract_address}")
            return
        
        await click_sol_and_forward(contract_address)
        return

    print("🔄 No valid contract address found in message.")

async def main():
    await client.start(phone_number)
    print(f"👀 Monitoring main group: {main_group_id}")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())