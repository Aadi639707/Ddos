import os
import time
import asyncio
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.raw.functions.channels import GetFullChannel
from pyrogram.raw.functions.phone import ToggleGroupCallSettings

load_dotenv()

try:
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    SESSION_STRING = os.getenv("SESSION_STRING")
    SUDO_USERS = [int(x) for x in os.getenv("SUDO_USERS", "").split(",") if x.strip()]
except Exception as e:
    print("❌ .env फाइल में डिटेल्स सही से नहीं डाली गई हैं!")
    exit(1)

app = Client("AdvancedAntiDdos", session_string=SESSION_STRING, api_id=API_ID, api_hash=API_HASH)

# Anti-Raid ट्रैकिंग डेटाबेस
JOIN_HISTORY = {}
SUSPICIOUS_USERS = {}  # अटैक करने वाले IDs को ट्रैक करने के लिए
RAID_LIMIT = 5  
TIME_WINDOW = 5 

@app.on_message(filters.new_chat_members)
async def vc_shield_and_udp_mitigation(client, message):
    chat_id = message.chat.id
    current_time = time.time()
    
    if chat_id not in JOIN_HISTORY:
        JOIN_HISTORY[chat_id] = []
        SUSPICIOUS_USERS[chat_id] = []
        
    JOIN_HISTORY[chat_id].append(current_time)
    
    # जो नए लोग आए हैं, उनकी IDs लिस्ट में डालो
    for user in message.new_chat_members:
        SUSPICIOUS_USERS[chat_id].append(user.id)
    
    # 5 सेकंड से पुरानी हिस्ट्री हटा दें
    JOIN_HISTORY[chat_id] = [t for t in JOIN_HISTORY[chat_id] if current_time - t <= TIME_WINDOW]
    
    # 🚨 सस्पीशियस एक्टिविटी / मास जॉइन डिटेक्ट हुआ
    if len(JOIN_HISTORY[chat_id]) >= RAID_LIMIT:
        try:
            peer = await client.resolve_peer(chat_id)
            full_chat = await client.invoke(GetFullChannel(channel=peer))
            call_info = full_chat.full_chat.call
            
            # 1. VC AUTO-MUTE (Audio Spam रोकने के लिए)
            if call_info:
                await client.invoke(ToggleGroupCallSettings(call=call_info, join_muted=True))
            
            # 2. UDP FLOOD MITIGATION (अटैकर का सर्वर कनेक्शन काटने के लिए)
            # जितने भी सस्पीशियस लोग इस 5 सेकंड की विंडो में आए हैं, सबको तुरंत बैन कर दो
            banned_count = 0
            for user_id in SUSPICIOUS_USERS[chat_id]:
                try:
                    await client.ban_chat_member(chat_id, user_id)
                    banned_count += 1
                except:
                    pass # अगर एडमिन है या कोई एरर है तो इग्नोर करो
                    
            await message.reply_text(
                "🚨 **DDoS / UDP Flood Attempt Detected!**\n"
                "🛡 **VC शील्ड ON:** नए यूज़र्स म्यूट कर दिए गए हैं।\n"
                f"⚔️ **UDP Mitigation:** {banned_count} सस्पीशियस बॉट्स का कनेक्शन काटकर उन्हें बैन कर दिया गया है।"
            )
            
            # डेटाबेस क्लियर करो
            JOIN_HISTORY[chat_id].clear() 
            SUSPICIOUS_USERS[chat_id].clear()
            
            # 5 मिनट (300 सेकंड) बाद VC वापस नॉर्मल (Unmute) कर दो
            await asyncio.sleep(300)
            
            full_chat_after = await client.invoke(GetFullChannel(channel=peer))
            call_info_after = full_chat_after.full_chat.call
            
            if call_info_after:
                await client.invoke(ToggleGroupCallSettings(call=call_info_after, join_muted=False))
                await message.reply_text("✅ **DDoS Alert Over.** स्थिति सामान्य है, VC अनम्यूट कर दी गई है।")
                
        except Exception as e:
            print(f"Shield Error: {e}")

# अगर कोई पहले से ग्रुप में है और ग्लिच कर रहा है, तो मैन्युअल कमांड
@app.on_message(filters.command("kickglitch", prefixes=".") & filters.user(SUDO_USERS))
async def manual_kick_glitcher(client, message):
    if not message.reply_to_message:
        return await message.reply_text("❌ जिस अकाउंट से ग्लिच हो रहा है, उसके मैसेज पर रिप्लाई करके `.kickglitch` लिखें।")
        
    user_id = message.reply_to_message.from_user.id
    chat_id = message.chat.id
    
    try:
        # बैन करने से उसका VC से सर्वर कनेक्शन तुरंत टूट जाएगा (UDP पैकेट्स ड्रॉप हो जाएंगे)
        await client.ban_chat_member(chat_id, user_id)
        await message.reply_text("✅ **UDP Mitigation:** ग्लिच करने वाले अकाउंट को सर्वर से डिस्कनेक्ट करके निकाल दिया गया है।")
    except Exception as e:
        await message.reply_text(f"❌ एरर: `{e}`")

if __name__ == "__main__":
    print("✅ Anti-DDoS Bot with UDP Mitigation Started!")
    app.run()
