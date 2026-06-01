import os
import time
import asyncio
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.raw.functions.channels import GetFullChannel
from pyrogram.raw.functions.phone import ToggleGroupCallSettings
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream

load_dotenv()

try:
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    SESSION_STRING = os.getenv("SESSION_STRING")
    SUDO_USERS = [int(x) for x in os.getenv("SUDO_USERS", "").split(",") if x.strip()]
except Exception as e:
    print("❌ .env फाइल में डिटेल्स सही से नहीं डाली गई हैं!")
    exit(1)

# Pyrogram Client
app = Client("AdvancedAntiDdos", session_string=SESSION_STRING, api_id=API_ID, api_hash=API_HASH)
# PyTgCalls Client (VC में बैठने के लिए)
call_py = PyTgCalls(app)

# Anti-Raid डेटाबेस
JOIN_HISTORY = {}
SUSPICIOUS_USERS = {}  
RAID_LIMIT = 5  
TIME_WINDOW = 5 
ACTIVE_CHATS = set() 

# ==========================================
# 🎤 1. VC JOIN & LEAVE COMMANDS (New)
# ==========================================
@app.on_message(filters.command("joinvc", prefixes=".") & filters.user(SUDO_USERS))
async def join_vc(client, message):
    chat_id = message.chat.id
    msg = await message.reply_text("⏳ **VC में जुड़ रहा हूँ...**")
    try:
        # बॉट को VC में 24/7 एक्टिव रखने के लिए एक लो-फाई/साइलेंट रेडियो लिंक प्ले कर रहे हैं
        # इससे टेलीग्राम बॉट को कभी बाहर नहीं निकालेगा।
        radio_url = "http://stream.zeno.fm/f3wvbbqmdg8uv" 
        await call_py.play(chat_id, MediaStream(radio_url))
        await msg.edit_text("✅ **मैं VC में बैठ गया हूँ!** (24/7 Active)")
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")

@app.on_message(filters.command("leavevc", prefixes=".") & filters.user(SUDO_USERS))
async def leave_vc(client, message):
    try:
        await call_py.leave_call(message.chat.id)
        await message.reply_text("✅ **VC से बाहर आ गया हूँ।**")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

# ==========================================
# 🛡️ 2. AUTOMATIC MASS JOIN & GLITCH SHIELD
# ==========================================
@app.on_message(filters.new_chat_members)
async def vc_shield_and_udp_mitigation(client, message):
    chat_id = message.chat.id
    current_time = time.time()
    ACTIVE_CHATS.add(chat_id) 
    
    if chat_id not in JOIN_HISTORY:
        JOIN_HISTORY[chat_id] = []
        SUSPICIOUS_USERS[chat_id] = []
        
    JOIN_HISTORY[chat_id].append(current_time)
    for user in message.new_chat_members:
        SUSPICIOUS_USERS[chat_id].append(user.id)
    
    JOIN_HISTORY[chat_id] = [t for t in JOIN_HISTORY[chat_id] if current_time - t <= TIME_WINDOW]
    
    if len(JOIN_HISTORY[chat_id]) >= RAID_LIMIT:
        try:
            peer = await client.resolve_peer(chat_id)
            full_chat = await client.invoke(GetFullChannel(channel=peer))
            call_info = full_chat.full_chat.call
            
            if call_info:
                await client.invoke(ToggleGroupCallSettings(call=call_info, join_muted=True))
            
            banned_count = 0
            for user_id in SUSPICIOUS_USERS[chat_id]:
                try:
                    await client.ban_chat_member(chat_id, user_id)
                    banned_count += 1
                except:
                    pass 
                    
            await message.reply_text(
                "🚨 **DDoS / Glitch Attempt Detected!**\n"
                "🛡 **VC शील्ड ON:** नए यूज़र्स ऑटो-म्यूट कर दिए गए हैं।\n"
                f"⚔️ **Auto-Kick:** {banned_count} सस्पीशियस बॉट्स को निकाल दिया गया है।"
            )
            
            JOIN_HISTORY[chat_id].clear() 
            SUSPICIOUS_USERS[chat_id].clear()
            
            await asyncio.sleep(300)
            full_chat_after = await client.invoke(GetFullChannel(channel=peer))
            call_info_after = full_chat_after.full_chat.call
            
            if call_info_after:
                await client.invoke(ToggleGroupCallSettings(call=call_info_after, join_muted=False))
                await message.reply_text("✅ **DDoS Alert Over.** VC शील्ड हटा दी गई है।")
                
        except Exception as e:
            print(f"Shield Error: {e}")

# ==========================================
# 🛠️ 3. MANUAL COMMANDS
# ==========================================
@app.on_message(filters.command("kickglitch", prefixes=".") & filters.user(SUDO_USERS))
async def manual_kick_glitcher(client, message):
    user_id = None
    
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    elif len(message.command) > 1:
        try:
            user = await client.get_users(message.command[1])
            user_id = user.id
        except Exception:
            return await message.reply_text("❌ यूज़र नहीं मिला। कृपया सही यूज़रनेम (जैसे @username) या ID टाइप करें।")
    else:
        return await message.reply_text("❌ इस्तेमाल का तरीका: किसी मैसेज पर रिप्लाई करें या `.kickglitch @username` लिखें।")
    
    try:
        await client.ban_chat_member(message.chat.id, user_id)
        await message.reply_text(f"✅ **Glitcher Kicked!** [{user_id}] का कनेक्शन सर्वर से काट दिया गया है।")
    except Exception as e:
        await message.reply_text(f"❌ एरर (शायद वह एडमिन है या ग्रुप में नहीं है): `{e}`")

@app.on_message(filters.command("vclock", prefixes=".") & filters.user(SUDO_USERS))
async def lock_vc(client, message):
    try:
        peer = await client.resolve_peer(message.chat.id)
        full_chat = await client.invoke(GetFullChannel(channel=peer))
        call_info = full_chat.full_chat.call
        if call_info:
            await client.invoke(ToggleGroupCallSettings(call=call_info, join_muted=True))
            await message.reply_text("🔒 **VC Lock:** अब VC में कोई भी नया बंदा माइक ऑन नहीं कर पाएगा।")
        else:
            await message.reply_text("❌ अभी कोई VC चालू नहीं है।")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("vcunlock", prefixes=".") & filters.user(SUDO_USERS))
async def unlock_vc(client, message):
    try:
        peer = await client.resolve_peer(message.chat.id)
        full_chat = await client.invoke(GetFullChannel(channel=peer))
        call_info = full_chat.full_chat.call
        if call_info:
            await client.invoke(ToggleGroupCallSettings(call=call_info, join_muted=False))
            await message.reply_text("🔓 **VC Unlock:** स्थिति सामान्य है। अब लोग माइक ऑन कर सकते हैं।")
    except Exception as e:
        pass

# ==========================================
# 🔄 4. AUTO BACKGROUND CHECK
# ==========================================
async def auto_vc_check():
    while True:
        await asyncio.sleep(300) 
        for chat_id in list(ACTIVE_CHATS):
            try:
                peer = await app.resolve_peer(chat_id)
                full_chat = await app.invoke(GetFullChannel(channel=peer))
                call_info = full_chat.full_chat.call
                if call_info:
                    print(f"[VC TICK] Chat {chat_id} - VC Active. Monitoring...")
                else:
                    print(f"[VC TICK] Chat {chat_id} - VC Offline.")
            except Exception:
                pass

async def main():
    await app.start()
    await call_py.start()
    print("✅ Advanced Anti-DDoS Bot (with VC Join) Started!")
    asyncio.create_task(auto_vc_check())
    from pyrogram import idle
    await idle()

if __name__ == "__main__":
    app.run(main())
