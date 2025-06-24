import os
import discord
from discord.ext import commands
from discord import Interaction, ButtonStyle
from discord.ui import View, Button
import requests
from dotenv import load_dotenv
from keep_alive import keep_alive

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
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

class AttendanceView(View):
    def __init__(self, user):
        super().__init__(timeout=None)
        self.user = user

    async def handle_selection(self, interaction: Interaction, time_label: str):
        if self.user in attendance_data:
            await interaction.response.send_message(f"{self.user} 已經出席過囉！", ephemeral=True)
        else:
            attendance_data[self.user] = time_label
            data = {
                DISCORD_NAME_ENTRY: self.user,
                TIME_ENTRY: time_label,
            }
            response = requests.post(GOOGLE_FORM_URL, data=data)
            await interaction.response.send_message(f"{self.user} 選擇了：{time_label}，已成功登記 ✅", ephemeral=True)
            print(f"📨 Submitted for {self.user}: {time_label} - Status: {response.status_code}")

    @discord.ui.button(label="19:30", style=ButtonStyle.primary)
    async def btn_1930(self, interaction: Interaction, button: Button):
        await self.handle_selection(interaction, "19:30")

    @discord.ui.button(label="19:45", style=ButtonStyle.primary)
    async def btn_1945(self, interaction: Interaction, button: Button):
        await self.handle_selection(interaction, "19:45")

    @discord.ui.button(label="20:00", style=ButtonStyle.primary)
    async def btn_2000(self, interaction: Interaction, button: Button):
        await self.handle_selection(interaction, "20:00")

    @discord.ui.button(label="領土期間", style=ButtonStyle.secondary)
    async def btn_領土(self, interaction: Interaction, button: Button):
        await self.handle_selection(interaction, "領土期間")

    @discord.ui.button(label="無法出席", style=ButtonStyle.danger)
    async def btn_無法(self, interaction: Interaction, button: Button):
        await self.handle_selection(interaction, "無法出席")


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ 已同步 {len(synced)} 個斜線指令")
    except Exception as e:
        print(f"❌ 同步指令失敗: {e}")

@bot.tree.command(name="出席", description="出席說明")
async def 出席(interaction: Interaction):
    user = str(interaction.user)
    view = AttendanceView(user)
    await interaction.response.send_message(
        f"{user} 請選擇你要出席的時間 👇",
        view=view,
        ephemeral=True
    )

@bot.command()
async def clear_attendance(ctx):
    attendance_data.clear()
    await ctx.send("✅ 所有簽到資料已清除")

print(f"環境變數 TOKEN: {TOKEN}")
keep_alive()
bot.run(TOKEN)
