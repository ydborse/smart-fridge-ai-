"""
Safe Telegram Bot API Configuration Diagnostic for Smart Fridge AI.
Tests environment loading, BotFather token validity, and Chat ID reachability
without printing or logging secrets.
"""
import sys
import asyncio
from app.config import settings
from app.services.notification import get_telegram_diagnostic

async def main():
    print("=" * 65)
    print(" Smart Fridge AI - Telegram Bot Configuration Diagnostic")
    print("=" * 65)
    
    diag = await get_telegram_diagnostic()

    print(f"TELEGRAM_ENABLED:       {diag.get('enabled')}")
    print(f"TELEGRAM_BOT_TOKEN:     {'Present' if diag.get('token_present') else 'MISSING'} ({diag.get('token_masked')}, length: {diag.get('token_length')})")
    print(f"TELEGRAM_CHAT_ID:       {'Present' if diag.get('chat_id_present') else 'MISSING'} ({diag.get('chat_id_masked')})")
    print(f"Overall Configured:     {diag.get('configured')}")
    print("-" * 65)

    if diag.get("bot_info"):
        b = diag["bot_info"]
        print(f"Bot Name:               {b.get('first_name')}")
        print(f"Bot Username:           @{b.get('username')}")
        print(f"Bot ID:                 {b.get('id')}")
        print(f"API Connectivity:       CONNECTED (200 OK)")
    else:
        print(f"API Connectivity:       FAILED ({diag.get('status')})")

    if diag.get("chat_verification"):
        c = diag["chat_verification"]
        if c.get("verified"):
            print(f"Chat Reachability:      VERIFIED (Type: {c.get('type')}, User: {c.get('first_name', '')})")
        else:
            print(f"Chat Reachability:      FAILED ({c.get('error')})")

    print("-" * 65)
    print(f"Status:                 {diag.get('status').upper()}")
    print(f"Diagnostic Detail:      {diag.get('detail')}")
    print("=" * 65)

    if diag.get("status") == "verified":
        print("RESULT: SUCCESS - Telegram Bot integration is correctly configured and reachable.")
        return 0
    else:
        print(f"RESULT: ISSUE DETECTED - {diag.get('detail')}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
