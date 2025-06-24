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
    def __init__(self):
        super().__init__(timeout=None)

    async def handle_selection(self, interaction: Interaction, time_label: str):
        member = interaction.guild.get_member(interaction.user.id)
        user = member.display_name if member else interaction.user.name

        if user in attendance_data:
            await interaction.response.send_message(f"{user} 已經出席過囉！", ephemeral=False)
        else:
            attendance_data[user] = time_label
            data = {
                DISCORD_NAME_ENTRY: user,
                TIME_ENTRY: time_label,
            }
            response = requests.post(GOOGLE_FORM_URL, data=data)
            await interaction.response.send_message(
                f"✅ {user} 選擇了：{time_label}，出席已登記", ephemeral=True
            )
            print(f"📨 Submitted for {user}: {time_label} - Status: {response.status_code}")

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
async def 出席(interaction: discord.Interaction):
    view = AttendanceView()  # ✅ 不傳 user
    await interaction.response.send_message("請選擇你的出席時間 👇", view=view)
    
@bot.tree.command(name="清空出席", description="清空所有出席資料")
async def 清空出席(interaction: discord.Interaction):
    # 檢查是否有管理員權限（可選）
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 你沒有權限清空出席資料。", ephemeral=True)
        return

    attendance_data.clear()
    await interaction.response.send_message("✅ 所有出席資料已清空", ephemeral=False)

@bot.command()
async def clear_attendance(ctx):
    attendance_data.clear()
    await ctx.send("✅ 所有簽到資料已清除")

print(f"環境變數 TOKEN: {TOKEN}")
keep_alive()
bot.run(TOKEN)
