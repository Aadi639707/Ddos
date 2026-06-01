import os
import time
import asyncio
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.raw.functions.channels import GetFullChannel
from pyrogram.raw.functions.phone import CreateGroupCall, DiscardGroupCall, ToggleGroupCallSettings
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream

# .env फाइल लोड करें
load_dotenv()

try:
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    SESSION_STRING = os.getenv("SESSION_STRING")
    # एडमिन IDs को लिस्ट में बदलें
    SUDO_USERS = [int(x) for x in os.getenv("SUDO_USERS", "").split(",") if x.strip()]
except Exception as e:
    print("❌ .env फाइल में डिटेल्स सही से नहीं डाली गई हैं!")
    exit(1)

# क्लाइंट सेटअप
app = Client("AdvancedAntiDdos", session_string=SESSION_STRING, api_id=API_ID, api_hash=API_HASH)
call_py = PyTgCalls(app)

# 24/7 साइलेंट स्ट्रीम URL (कोई गाना नहीं, बिल्कुल सन्नाटा)
SILENT_URL = "http://stream.zeno.fm/0w8as7yk00duv"

# एंटी-रेड और ट्रैकिंग डेटाबेस
JOIN_HISTORY = {}
SUSPICIOUS_USERS = {}  
RAID_LIMIT = 5  
TIME_WINDOW = 5 
ACTIVE_CHATS = set() 

# ==========================================
# 🔄 1. SMART IP CHANGER (Panic Button)
# ==========================================
@app.on_message(filters.command("fixvc", prefixes=".") & filters.user(SUDO_USERS))
async def fix_vc_and_change_ip(client, message):
    chat_id = message.chat.id
    msg = await message.reply_text("⏳ **DDoS डिटेक्टेड! IP एड्रेस बदला जा रहा है...**")
    
    try:
        # 1. बॉट को वीसी से निकालें
        try:
            await call_py.leave_call(chat_id)
        except:
            pass
            
        peer = await client.resolve_peer(chat_id)
        full_chat = await client.invoke(GetFullChannel(channel=peer))
        call_info = full_chat.full_chat.call
        
        # 2. पुरानी वीसी एंड करें (IP का कनेक्शन तोड़ने के लिए)
        if call_info:
            await client.invoke(DiscardGroupCall(call=call_info))
            await asyncio.sleep(1) 
            
        # 3. नई वीसी बनाएं (नया फ्रेश IP सर्वर लेने के लिए)
        random_id = int(time.time())
        await client.invoke(CreateGroupCall(peer=peer, random_id=random_id))
        await asyncio.sleep(1)
        
        # 4. बॉट वापस साइलेंट मोड में बैठेगा
        await call_py.play(chat_id, MediaStream(SILENT_URL))
        
        await msg.edit_text("✅ **IP एड्रेस सफलता से बदल दिया गया!**\nपुराना DDoS अटैक फेल हो गया है और नई VC चालू है।")
    except Exception as e:
        await msg.edit_text(f"❌ **IP चेंज एरर:** `{e}`")

# ==========================================
# 🎤 2. 24/7 SILENT VC HOLDER
# ==========================================
@app.on_message(filters.command("joinvc", prefixes=".") & filters.user(SUDO_USERS))
async def join_vc(client, message):
    chat_id = message.chat.id
    msg = await message.reply_text("⏳ **VC में साइलेंट मोड में जुड़ रहा हूँ...**")
    try:
        ACTIVE_CHATS.add(chat_id)
        await call_py.play(chat_id, MediaStream(SILENT_URL))
        await msg.edit_text("✅ **मैं VC में बैठ गया हूँ!** (No Sound - 24/7 Active)")
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")

@app.on_message(filters.command("leavevc", prefixes=".") & filters.user(SUDO_USERS))
async def leave_vc(client, message):
    try:
        ACTIVE_CHATS.discard(message.chat.id)
        await call_py.leave_call(message.chat.id)
        await message.reply_text("✅ **VC से बाहर आ गया हूँ।**")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

# ==========================================
# 🛡️ 3. AUTO-SHIELD (UDP/Mass Join Mitigation)
# ==========================================
@app.on_message(filters.new_chat_members)
async def vc_shield(client, message):
    chat_id = message.chat.id
    current_time = time.time()
    
    if chat_id not in JOIN_HISTORY:
        JOIN_HISTORY[chat_id] = []
        SUSPICIOUS_USERS[chat_id] = []
        
    JOIN_HISTORY[chat_id].append(current_time)
    for user in message.new_chat_members:
        SUSPICIOUS_USERS[chat_id].append(user.id)
    
    JOIN_HISTORY[chat_id] = [t for t in JOIN_HISTORY[chat_id] if current_time - t <= TIME_WINDOW]
    
    # अगर रेड/DDoS डिटेक्ट हो
    if len(JOIN_HISTORY[chat_id]) >= RAID_LIMIT:
        try:
            peer = await client.resolve_peer(chat_id)
            full_chat = await client.invoke(GetFullChannel(channel=peer))
            call_info = full_chat.full_chat.call
            
            if call_info:
                # नए लोगों को ऑटो-म्यूट करो
                await client.invoke(ToggleGroupCallSettings(call=call_info, join_muted=True))
            
            banned_count = 0
            for user_id in SUSPICIOUS_USERS[chat_id]:
                try:
                    await client.ban_chat_member(chat_id, user_id)
                    banned_count += 1
                except:
                    pass 
                    
            await message.reply_text(f"🚨 **DDoS Attempt Detected!**\n🛡 **VC Shield ON:** नए यूज़र्स म्यूट हैं।\n⚔️ **Auto-Kick:** {banned_count} सस्पीशियस आईडी निकाली गईं।")
            
            JOIN_HISTORY[chat_id].clear() 
            SUSPICIOUS_USERS[chat_id].clear()
            
            # 5 मिनट बाद वापस नॉर्मल
            await asyncio.sleep(300)
            full_chat_after = await client.invoke(GetFullChannel(channel=peer))
            call_info_after = full_chat_after.full_chat.call
            
            if call_info_after:
                await client.invoke(ToggleGroupCallSettings(call=call_info_after, join_muted=False))
                await message.reply_text("✅ **DDoS Alert Over.** VC शील्ड हट गई है।")
        except Exception as e:
            print(f"Shield Error: {e}")

# ==========================================
# 🛠️ 4. MANUAL KICK & LOCK COMMANDS
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
            return await message.reply_text("❌ यूज़र नहीं मिला। @username या ID इस्तेमाल करें।")
    else:
        return await message.reply_text("❌ रिप्लाई करें या `.kickglitch @username` लिखें।")
    
    try:
        await client.ban_chat_member(message.chat.id, user_id)
        await message.reply_text(f"✅ **Glitcher Kicked!** [{user_id}] का सर्वर कनेक्शन कट गया।")
    except Exception as e:
        await message.reply_text(f"❌ एरर: `{e}`")

@app.on_message(filters.command("vclock", prefixes=".") & filters.user(SUDO_USERS))
async def lock_vc(client, message):
    try:
        peer = await client.resolve_peer(message.chat.id)
        full_chat = await client.invoke(GetFullChannel(channel=peer))
        call_info = full_chat.full_chat.call
        if call_info:
            await client.invoke(ToggleGroupCallSettings(call=call_info, join_muted=True))
            await message.reply_text("🔒 **VC Lock:** नए लोग माइक ऑन नहीं कर पाएंगे।")
    except Exception as e:
        pass

@app.on_message(filters.command("vcunlock", prefixes=".") & filters.user(SUDO_USERS))
async def unlock_vc(client, message):
    try:
        peer = await client.resolve_peer(message.chat.id)
        full_chat = await client.invoke(GetFullChannel(channel=peer))
        call_info = full_chat.full_chat.call
        if call_info:
            await client.invoke(ToggleGroupCallSettings(call=call_info, join_muted=False))
            await message.reply_text("🔓 **VC Unlock:** लोग अब माइक ऑन कर सकते हैं।")
    except Exception as e:
        pass

# ==========================================
# 🔄 5. BACKGROUND VC MONITOR
# ==========================================
async def auto_vc_check():
    while True:
        await asyncio.sleep(300) # हर 5 मिनट
        for chat_id in list(ACTIVE_CHATS):
            try:
                peer = await app.resolve_peer(chat_id)
                full_chat = await app.invoke(GetFullChannel(channel=peer))
                call_info = full_chat.full_chat.call
                if not call_info:
                    print(f"Chat {chat_id} - VC Offline.")
            except Exception:
                pass

async def main():
    await app.start()
    await call_py.start()
    print("✅ Advanced Anti-DDoS Bot Started!")
    asyncio.create_task(auto_vc_check())
    from pyrogram import idle
    await idle()

if __name__ == "__main__":
    app.run(main())
