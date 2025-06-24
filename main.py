import os
import discord
from discord.ext import commands
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")  # 請確認 .env 裡是 TOKEN，不是 DISCORD_TOKEN
GOOGLE_FORM_URL = os.getenv("GOOGLE_FORM_URL")
DISCORD_NAME_ENTRY = os.getenv("DISCORD_NAME_ENTRY")
TIME_ENTRY = os.getenv("TIME_ENTRY")

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

attendance_data = {}

emoji_time_map = {
    "🇦": "19:30",
    "🇧": "19:45",
    "🇨": "20:00",
    "🇩": "領土期間",
    "🇪": "無法參加",
}

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ 已同步 {len(synced)} 個斜線指令")
    except Exception as e:
        print(f"❌ 同步指令失敗: {e}")

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return

    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    username = str(member)

    if username in attendance_data:
        return

    emoji = str(payload.emoji)
    if emoji in emoji_time_map:
        selected_time = emoji_time_map[emoji]
        attendance_data[username] = selected_time

        data = {
            DISCORD_NAME_ENTRY: username,
            TIME_ENTRY: selected_time,
        }
        response = requests.post(GOOGLE_FORM_URL, data=data)
        print(f"📨 Submitted for {username}: {selected_time} - Status: {response.status_code}")

@bot.tree.command(name="出席", description="出席說明")
async def 出席(interaction: discord.Interaction):
    user = str(interaction.user)
    if user in attendance_data:
        await interaction.response.send_message(f"{user} 已經出席過囉！", ephemeral=True)
    else:
        await interaction.response.send_message(f"{user} 請點選訊息上的表情符號完成出席喔 👇", ephemeral=True)

@bot.command()
async def clear_attendance(ctx):
    attendance_data.clear()
    await ctx.send("✅ 所有簽到資料已清除")

bot.run(TOKEN)

