import os
import time
import asyncio
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import ChatPermissions
from pyrogram.raw.functions.phone import CreateGroupCall, DiscardGroupCall
from pyrogram.raw.functions.channels import GetFullChannel

# .env फाइल से डेटा लोड करें
load_dotenv()

try:
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    SESSION_STRING = os.getenv("SESSION_STRING")
    SUDO_USERS = [int(x) for x in os.getenv("SUDO_USERS", "").split(",") if x.strip()]
except Exception as e:
    print("❌ .env फाइल में डिटेल्स सही से नहीं डाली गई हैं!")
    exit(1)

# Pyrogram Client Setup
app = Client("AntiDdosUserbot", session_string=SESSION_STRING, api_id=API_ID, api_hash=API_HASH)

# Anti-Raid का डेटाबेस
JOIN_HISTORY = {}
RAID_LIMIT = 5  # अगर 5 सेकंड के अंदर 5 से ज्यादा लोग आते हैं
TIME_WINDOW = 5 

@app.on_message(filters.new_chat_members)
async def anti_raid(client, message):
    chat_id = message.chat.id
    current_time = time.time()
    
    if chat_id not in JOIN_HISTORY:
        JOIN_HISTORY[chat_id] = []
        
    JOIN_HISTORY[chat_id].append(current_time)
    
    # पुरानी हिस्ट्री (5 सेकंड से पहले वाली) लिस्ट से हटा दें
    JOIN_HISTORY[chat_id] = [t for t in JOIN_HISTORY[chat_id] if current_time - t <= TIME_WINDOW]
    
    # अगर लिमिट क्रॉस होती है (DDoS / Mass Join)
    if len(JOIN_HISTORY[chat_id]) >= RAID_LIMIT:
        try:
            # तुरंत ग्रुप में मैसेजिंग बंद कर दें (Lock Group)
            await client.set_chat_permissions(
                chat_id,
                ChatPermissions(can_send_messages=False)
            )
            msg = await message.reply_text("🚨 **Mass Join / Raid Detected!**\nसुरक्षा के लिए ग्रुप को लॉक कर दिया गया है।")
            
            # हिस्ट्री क्लियर कर दें ताकि बॉट बार-बार लॉक कमांड न भेजे
            JOIN_HISTORY[chat_id].clear() 
            
            # 5 मिनट (300 सेकंड) बाद ग्रुप को वापस अपने आप अनलॉक करें
            await asyncio.sleep(300)
            await client.set_chat_permissions(
                chat_id,
                ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_send_polls=True,
                    can_add_web_page_previews=True
                )
            )
            await msg.edit_text("✅ **Raid Alert Over.** स्थिति सामान्य है, ग्रुप को अनलॉक कर दिया गया है।")
        except Exception as e:
            print(f"Anti-Raid Error: {e}")

@app.on_message(filters.command("fixvc", prefixes=".") & filters.user(SUDO_USERS))
async def restart_vc(client, message):
    chat_id = message.chat.id
    msg = await message.reply_text("🔄 **VC Restart की जा रही है...**")
    
    try:
        peer = await client.resolve_peer(chat_id)
        
        # ग्रुप/चैनल का पूरा डेटा निकालें ताकि पुरानी VC का ऑब्जेक्ट मिल सके
        full_chat = await client.invoke(GetFullChannel(channel=peer))
        call_info = full_chat.full_chat.call
        
        # अगर पहले से कोई VC चल रही है, तो उसे बंद (Discard) करें
        if call_info:
            await client.invoke(DiscardGroupCall(call=call_info))
            await asyncio.sleep(1.5) # सर्वर को प्रोसेस करने का थोड़ा समय दें
            
        # तुरंत एक नई VC शुरू करें
        random_id = int(time.time())
        await client.invoke(CreateGroupCall(peer=peer, random_id=random_id))
        
        await msg.edit_text("✅ **VC Restart Success!**\nनया IP असाइन हो चुका है और ग्लिच फिक्स हो गया है।")
    except Exception as e:
        await msg.edit_text(f"❌ **VC रीस्टार्ट करने में एरर आया:** `{e}`")

if __name__ == "__main__":
    print("✅ Anti-DDoS Userbot Started Successfully!")
    app.run()
