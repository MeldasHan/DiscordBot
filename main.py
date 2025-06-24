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
GOOGLE_SCRIPT_URL = os.getenv("GOOGLE_SCRIPT_URL")
DISCORD_NAME_ENTRY = os.getenv("DISCORD_NAME_ENTRY")
TIME_ENTRY = os.getenv("TIME_ENTRY")

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

attendance_data = {}

def get_locale_text(locale: str):
    if "ja" in locale:
        return {
            "select_prompt": "出席時間を選んでください 👇",
            "already_checked": "あなたは既に出席しています！",
            "checked_success": "✅ {user} が「{time}」を選択しました。出席を記録しました。",
            "cleared": "✅ 出席データをすべてクリアしました。",
            "no_permission_clear": "❌ 出席データをクリアする権限がありません。",
            "no_permission": "❌ この操作を実行する権限がありません。",
            "signed_in": "✅ 出席済み：{count}人\n{list}",
            "not_signed_in": "❌ 未出席：{count}人\n{list}",
            "group_summary": "📊 ロール「{role}」の出席状況：\n{signed}\n\n{not_signed}",
        }
    else:
        return {
            "select_prompt": "請選擇你的出席時間 👇",
            "already_checked": "{user} 已經出席過囉！",
            "checked_success": "✅ {user} 選擇了：{time}，出席已登記",
            "cleared": "✅ 所有出席資料已清空",
            "no_permission_clear": "❌ 你沒有權限清空出席資料。",
            "no_permission": "❌ 你沒有權限使用這個指令。",
            "signed_in": "✅ 已簽到：{count} 人\n{list}",
            "not_signed_in": "❌ 未簽到：{count} 人\n{list}",
            "group_summary": "📊 身分組 **{role}** 簽到狀況：\n{signed}\n\n{not_signed}",
        }

class AttendanceView(View):
    def __init__(self, interaction: Interaction):
        super().__init__(timeout=None)
        self.offset = self._estimate_utc_offset(interaction)
        self.locale = str(interaction.locale)

        time_options = ["19:30", "19:45", "20:00"]
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
            return 8 - 8
        elif "ja" in locale or "ko" in locale:
            return 9 - 8
        elif "en" in locale:
            return 0 - 8
        else:
            return 0

    def _make_button(self, label, time_value, style):
        view_self = self

        async def callback(interaction: Interaction):
            await view_self.handle_selection(interaction, time_value)

        button = Button(label=label, style=style)
        button.callback = callback
        return button

    async def handle_selection(self, interaction: Interaction, time_label: str):
        texts = get_locale_text(str(interaction.locale))
        member = interaction.guild.get_member(interaction.user.id)
        user = member.display_name if member else interaction.user.name
        user_id = interaction.user.id

        if user_id in attendance_data:
            await interaction.response.send_message(
                texts["already_checked"].replace("{user}", user), ephemeral=True
            )
        else:
            attendance_data[user_id] = time_label

            data = {
                DISCORD_NAME_ENTRY: user,
                TIME_ENTRY: time_label,
            }
            response = requests.post(GOOGLE_FORM_URL, data=data)
            await interaction.response.send_message(
                texts["checked_success"].format(user=user, time=time_label), ephemeral=True
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
    texts = get_locale_text(str(interaction.locale))
    await interaction.response.defer(ephemeral=False)
    view = AttendanceView(interaction)
    await interaction.followup.send(texts["select_prompt"], view=view, ephemeral=False)

@bot.tree.command(name="清空出席", description="清空所有出席資料")
async def 清空出席(interaction: discord.Interaction):
    texts = get_locale_text(str(interaction.locale))
    allowed_role_ids = [
        983698693431640064, 1229072929636093973,
        983703371871563807, 983708819215482911,
        1103689405752954960, 1317669500644229130
    ]

    if not interaction.user.guild_permissions.administrator:
        if not any(r.id in allowed_role_ids for r in interaction.user.roles):
            await interaction.response.send_message(texts["no_permission_clear"], ephemeral=True)
            return

    attendance_data.clear()
    try:
        res = requests.get(GOOGLE_SCRIPT_URL)
        print("✅ Google 表單清除" if res.status_code == 200 else f"⚠️ 清除失敗：{res.status_code}")
    except Exception as e:
        print(f"❌ 無法連線：{e}")
    await interaction.response.send_message(texts["cleared"], ephemeral=False)

@bot.tree.command(name="簽到統計", description="查看某身分組的簽到與未簽到成員")
@app_commands.describe(role="想要統計的身分組")
async def 簽到統計(interaction: discord.Interaction, role: discord.Role):
    texts = get_locale_text(str(interaction.locale))
    allowed_role_ids = [
        983698693431640064, 1229072929636093973,
        983703371871563807, 983708819215482911,
        1103689405752954960, 1317669500644229130
    ]

    if not interaction.user.guild_permissions.administrator:
        if not any(r.id in allowed_role_ids for r in interaction.user.roles):
            await interaction.response.send_message(texts["no_permission"], ephemeral=True)
            return

    signed_in = []
    not_signed_in = []

    for member in role.members:
        if member.id in attendance_data:
            signed_in.append(member.display_name)
        else:
            not_signed_in.append(member.display_name)

    msg = texts["group_summary"].format(
        role=role.name,
        signed=texts["signed_in"].format(count=len(signed_in), list="、".join(signed_in) or "（なし）"),
        not_signed=texts["not_signed_in"].format(count=len(not_signed_in), list="、".join(not_signed_in) or "（全員出席）")
    )
    await interaction.response.send_message(msg, ephemeral=True)

@bot.command()
async def clear_attendance(ctx):
    attendance_data.clear()
    await ctx.send("✅ 所有簽到資料已清除")

print(f"環境變數 TOKEN: {TOKEN}")
keep_alive()
bot.run(TOKEN)
