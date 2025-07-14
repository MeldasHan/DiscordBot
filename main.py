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
    def __init__(self):
        super().__init__(timeout=None)

        time_options = ["19:30", "19:45", "20:00"]
        for t in time_options:
            self.add_item(self._make_button(label=t, time_value=t, style=ButtonStyle.primary))

        self.add_item(self._make_button("領土期間", "領土期間", ButtonStyle.secondary))
        self.add_item(self._make_button("無法出席", "無法出席", ButtonStyle.danger))

    def _make_button(self, label, time_value, style):
        button = Button(label=label, style=style, custom_id=f"attend:{time_value}")

        async def callback(interaction: Interaction):
            await AttendanceView.handle_selection(interaction, time_value)

        button.callback = callback
        return button

    @staticmethod
    async def handle_selection(interaction: Interaction, time_label: str):
        # 和你原來的 handle_selection 相同，只是現在是 staticmethod
        texts = get_locale_text(str(interaction.locale))
        member = interaction.guild.get_member(interaction.user.id)
        user = member.display_name if member else interaction.user.name

        if user in attendance_data:
            await interaction.response.send_message(
                texts["already_checked"].replace("{user}", user), ephemeral=True
            )
        else:
            attendance_data[user] = time_label
            try:
                response = requests.post(GOOGLE_FORM_URL, data={
                    DISCORD_NAME_ENTRY: user,
                    TIME_ENTRY: time_label,
                }, timeout=3)
                print(f"📨 Submitted for {user}: {time_label} - Status: {response.status_code}")
            except requests.RequestException as e:
                print(f"❌ Google 表單錯誤: {e}")

            await interaction.response.send_message(
                texts["checked_success"].format(user=user, time=time_label), ephemeral=True
            )
            
def fetch_attendance_from_sheet() -> str:
    global attendance_data, last_sync_status, last_sync_time
    try:
        response = requests.get(os.getenv("GOOGLE_FETCH_URL"))
        if response.status_code == 200:
            rows = response.json()
            attendance_data.clear()
            for row in rows:
                user = row.get("DC ID")
                time = row.get("出席時間")
                if user and time:
                    attendance_data[user] = time
            last_sync_time = datetime.utcnow() + timedelta(hours=8)
            last_sync_status = f"✅ 成功同步 {len(attendance_data)} 筆出席資料 (最後同步時間：{last_sync_time.strftime('%Y-%m-%d %H:%M:%S')})"
            return last_sync_status
        else:
            last_sync_status = f"⚠️ Google Script 回傳非 200：{response.status_code}"
            return last_sync_status
    except Exception as e:
        last_sync_status = f"❌ 同步失敗：{e}"
        return last_sync_status

@bot.tree.command(name="出席", description="出席說明")
async def 出席(interaction: discord.Interaction):
    texts = get_locale_text(str(interaction.locale))
    await interaction.response.send_message(
        texts["select_prompt"],
        view=AttendanceView(),
        ephemeral=False
    )
    
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
    allowed_role_ids = [
        983698693431640064, 1229072929636093973,
        983703371871563807, 983708819215482911,
        1103689405752954960, 1317669500644229130
    ]

    if not interaction.user.guild_permissions.administrator:
        if not any(r.id in allowed_role_ids for r in interaction.user.roles):
            await interaction.response.send_message("❌ 你沒有權限使用這個指令。", ephemeral=True)
            return

    await interaction.response.defer(ephemeral=True)

    signed_in = [m.display_name for m in role.members if m.display_name in attendance_data]
    not_signed_in = [m.display_name for m in role.members if m.display_name not in attendance_data]

    msg = (
        f"{last_sync_status}\n\n"  # 顯示最後同步狀態
        f"📊 身分組 **{role.name}** 簽到狀況：\n"
        f"✅ 已簽到：{len(signed_in)} 人\n"
        f"{'、'.join(signed_in) if signed_in else '（無人簽到）'}\n\n"
        f"❌ 未簽到：{len(not_signed_in)} 人\n"
        f"{'、'.join(not_signed_in) if not_signed_in else '（全員簽到）'}"
    )

    await interaction.followup.send(msg, ephemeral=True)
    
@bot.tree.command(name="同步資料", description="當Bot同步失敗時可以呼叫")
async def 同步資料(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)  # 預先回應，避免 3 秒 Timeout
    sync_status = fetch_attendance_from_sheet()
    await interaction.followup.send(sync_status, ephemeral=True)
    
@bot.tree.command(name="同步指令", description="同步Bot的指令")
@commands.is_owner()
async def sync(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    synced = await bot.tree.sync()
    await interaction.followup.send(f"Synced {len(synced)} commands.", ephemeral=True)    

@bot.command()
async def clear_attendance(ctx):
    attendance_data.clear()
    await ctx.send("✅ 所有簽到資料已清除")
    
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        bot.add_view(AttendanceView())  # ✅ 註冊 Persistent View
        print(f"✅ on_ready 同步了 {len(synced)} 個指令")
    except Exception as e:
        print(f"❌ 同步失敗: {e}")

# 加入條件避免非必要情況執行 bot.run()
if os.getenv("RUN_DISCORD_BOT", "true").lower() == "true":
    keep_alive()  # ✅ 先開啟 Flask ping server（非阻塞）
    
    import asyncio
    async def main():
        await asyncio.sleep(5)  # 延遲以保證 Google Script 不過載
        fetch_attendance_from_sheet()
        print(f"🔄 啟動時自動同步結果：{last_sync_status}")
        await bot.start(TOKEN)

    asyncio.run(main())

else:
    print("⏸️ UptimeRobot pinged: 跳過 bot.run()")
    keep_alive()  # 只開 Flask server，不跑 bot


