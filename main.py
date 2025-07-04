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

        if user in attendance_data:
            await interaction.response.send_message(
                texts["already_checked"].replace("{user}", user), ephemeral=True
            )
        else:
            attendance_data[user] = time_label  # ✅ 用 display name 作為 key

            data = {
                DISCORD_NAME_ENTRY: user,  # 表單裡這是暱稱欄位
                TIME_ENTRY: time_label,
            }
            response = requests.post(GOOGLE_FORM_URL, data=data)
            await interaction.response.send_message(
                texts["checked_success"].format(user=user, time=time_label), ephemeral=True
            )
            print(f"📨 Submitted for {user}: {time_label} - Status: {response.status_code}")

            
def fetch_attendance_from_sheet() -> str:
    global attendance_data
    try:
        response = requests.get(os.getenv("GOOGLE_FETCH_URL"))
        print("🔔 Response status:", response.status_code)
        print("🔔 Response text:", response.text)  # 先看文字是否正常
        
        if response.status_code == 200:
            rows = response.json()  # 這裡解析成功
            attendance_data.clear()
            for row in rows:
                user = row.get("DC ID")  # 這裡改成 "DC ID" 才對
                time = row.get("出席時間")
                if user and time:
                    attendance_data[user] = time
            return f"✅ 成功同步 {len(attendance_data)} 筆出席資料"
        else:
            return f"⚠️ Google Script 回傳非 200：{response.status_code}"
    except Exception as e:
        return f"❌ 同步失敗：{e}"

@bot.tree.command(name="出席", description="出席說明")
async def 出席(interaction: discord.Interaction):
    texts = get_locale_text(str(interaction.locale))
    await interaction.response.defer(ephemeral=False)
    view = AttendanceView(interaction)
    await interaction.followup.send(texts["select_prompt"], view=view, ephemeral=False)
    
@bot.tree.command(name="清空出席", description="清空所有出席資料")
async def 清空出席(interaction: discord.Interaction):
    allowed_role_ids = [
        983698693431640064, 1229072929636093973,
        983703371871563807, 983708819215482911,
        1103689405752954960, 1317669500644229130
    ]

    # ✅ 預先 defer response，避免 3 秒 timeout，同時讓後續可以用 followup 回應
    await interaction.response.defer(ephemeral=False)

    if not interaction.user.guild_permissions.administrator:
        if not any(r.id in allowed_role_ids for r in interaction.user.roles):
            await interaction.followup.send("❌ 你沒有權限清空出席資料。", ephemeral=True)
            return

    attendance_data.clear()

    try:
        res = requests.get(GOOGLE_SCRIPT_URL)
        if res.status_code == 200:
            print("✅ Google 表單回覆已清除")
        else:
            print(f"⚠️ Google 表單清除失敗：{res.status_code}")
    except Exception as e:
        print(f"❌ 無法連線到 Google Script：{e}")

    # ✅ 改用 followup.send，而不是 response.send_message
    await interaction.followup.send("✅ 所有出席資料已清空", ephemeral=False)

@bot.tree.command(name="簽到統計", description="查看某身分組的簽到與未簽到成員")
@app_commands.describe(role="想要統計的身分組")
async def 簽到統計(interaction: discord.Interaction, role: discord.Role):
    allowed_role_ids = [983698693431640064, 1229072929636093973, 983703371871563807,
                        983708819215482911, 1103689405752954960, 1317669500644229130]

    if not interaction.user.guild_permissions.administrator:
        if not any(r.id in allowed_role_ids for r in interaction.user.roles):
            await interaction.response.send_message("❌ 你沒有權限使用這個指令。", ephemeral=True)
            return

    await interaction.response.defer(ephemeral=True)

    # 建議這邊改成非阻塞，或加上 try-except 防止出錯
    try:
        sync_status = fetch_attendance_from_sheet()  # 同步，並取得狀態文字
    except Exception as e:
        await interaction.followup.send(f"❌ 同步失敗: {e}", ephemeral=True)
        return

    signed_in = []
    not_signed_in = []

    for member in role.members:
        # 根據你資料的 key 是名稱或 ID，這裡要一致
        if member.display_name in attendance_data:
            signed_in.append(member.display_name)
        else:
            not_signed_in.append(member.display_name)

    msg = (
        f"{sync_status}\n\n"  # ⬅️ 同步狀態加在最前面
        f"📊 身分組 **{role.name}** 簽到狀況：\n"
        f"✅ 已簽到：{len(signed_in)} 人\n"
        f"{'、'.join(signed_in) if signed_in else '（無人簽到）'}\n\n"
        f"❌ 未簽到：{len(not_signed_in)} 人\n"
        f"{'、'.join(not_signed_in) if not_signed_in else '（全員簽到）'}"
    )

    await interaction.followup.send(msg, ephemeral=True)



@bot.command()
async def clear_attendance(ctx):
    attendance_data.clear()
    await ctx.send("✅ 所有簽到資料已清除")

print(f"環境變數 TOKEN: {TOKEN}")

# 啟動 Flask web server（給 UptimeRobot ping 使用）
keep_alive()

# 加入條件避免非必要情況執行 bot.run()
if os.getenv("RUN_DISCORD_BOT", "true").lower() == "true":
    import asyncio

    async def main():
        await asyncio.sleep(5)  # 加點延遲避免連續重啟 API 過載
        await bot.start(TOKEN)

    asyncio.run(main())
else:
    print("⏸️ UptimeRobot pinged: 跳過 bot.run()")

