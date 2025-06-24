import os
import discord
from discord.ext import commands
from discord import Interaction, ButtonStyle
from discord.ui import View, Button
from discord import app_commands
import requests
from dotenv import load_dotenv
from keep_alive import keep_alive
from datetime import datetime, timedelta

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
    def __init__(self, interaction: Interaction):
        super().__init__(timeout=None)

        # 預設 UTC offset，可依 interaction.locale 判斷
        self.offset = self._estimate_utc_offset(interaction)

        # 對應的原始時間（送出的固定值）
        time_options = ["11:30", "11:45", "12:00"]
        for t in time_options:
            label = self._convert_time_label(t)
            self.add_item(self._make_button(label, t, ButtonStyle.primary))

        self.add_item(self._make_button("領土期間", "領土期間", ButtonStyle.secondary))
        self.add_item(self._make_button("無法出席", "無法出席", ButtonStyle.danger))

    def _convert_time_label(self, base_time_str):
        base_time = datetime.strptime(base_time_str, "%H:%M")
        local_time = base_time + timedelta(hours=self.offset)
        return local_time.strftime("%H:%M")

    def _estimate_utc_offset(self, interaction):
        locale = str(interaction.locale)
        if "zh" in locale:
            return 8
        elif "ja" in locale:
            return 9
        elif "ko" in locale:
            return 9
        elif "en" in locale:
            return 0
        else:
            return 8  # 預設 +8（台灣）

    def _make_button(self, label, time_value, style):
        view_self = self  # 🔁 把 self 存到 closure 變數中

        async def callback(interaction: Interaction):
            await view_self.handle_selection(interaction, time_value)

        button = Button(label=label, style=style)
        button.callback = callback
        return button

    async def handle_selection(self, interaction: Interaction, time_label: str):
        member = interaction.guild.get_member(interaction.user.id)
        user = member.display_name if member else interaction.user.name
        user_id = interaction.user.id

        if user_id in attendance_data:
            await interaction.response.send_message(f"{user} 已經出席過囉！", ephemeral=True)
        else:
            attendance_data[user_id] = time_label
            data = {
                DISCORD_NAME_ENTRY: user,
                TIME_ENTRY: time_label,
            }
            response = requests.post(GOOGLE_FORM_URL, data=data)
            await interaction.response.send_message(
                f"✅ {user} 選擇了：{time_label}，出席已登記", ephemeral=True
            )
            print(f"📨 Submitted for {user}: {time_label} - Status: {response.status_code}")

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
    await interaction.response.defer(ephemeral=True)  # 👈 先佔住，避免 3 秒 timeout

    view = AttendanceView(interaction)
    await interaction.followup.send("請選擇你的出席時間 👇", view=view, ephemeral=True))
    
@bot.tree.command(name="清空出席", description="清空所有出席資料")
async def 清空出席(interaction: discord.Interaction):
    # 檢查是否有管理員權限（可選）
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 你沒有權限清空出席資料。", ephemeral=True)
        return

    attendance_data.clear()
    await interaction.response.send_message("✅ 所有出席資料已清空", ephemeral=False)
    
@bot.tree.command(name="簽到統計", description="查看某身分組的簽到人數")
@app_commands.describe(role="想要統計的身分組")
async def 簽到統計(interaction: discord.Interaction, role: discord.Role):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 你沒有權限使用這個指令。", ephemeral=True)
        return

    guild = interaction.guild
    total = 0
    matched_names = []

    for member in role.members:
        uid = str(member.id)
        if uid in attendance_data:
            total += 1
            matched_names.append(member.display_name)

    await interaction.response.send_message(
        f"📊 身分組 **{role.name}** 中共有 **{total}** 人簽到過。\n"
        f"{'、'.join(matched_names) if matched_names else '（無人簽到）'}",
        ephemeral=True
    )

@bot.command()
async def clear_attendance(ctx):
    attendance_data.clear()
    await ctx.send("✅ 所有簽到資料已清除")

print(f"環境變數 TOKEN: {TOKEN}")
keep_alive()
bot.run(TOKEN)
