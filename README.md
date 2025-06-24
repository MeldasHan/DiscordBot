# Discord 出席簽到機器人

### ✅ 功能
- A～E 表情符號代表出席選項
- 自動填寫 Google 表單
- 防止重複簽到
- `!clear_attendance` 清除紀錄

### 🚀 Render 部署步驟

1. 到 [Render](https://render.com/) 建立帳號
2. 點選 `New +` → `Web Service`
3. 選擇 `Deploy an existing project`
4. 上傳此 ZIP 解壓縮後的資料夾
5. 設定以下項目：
   - Start Command: `python keep_alive.py & python main.py`
   - Environment: `Python 3`
   - 建立以下環境變數：
     - `DISCORD_TOKEN`
     - `GOOGLE_FORM_URL` → https://docs.google.com/forms/d/e/你的表單ID/formResponse
     - `DISCORD_NAME_ENTRY` → entry.1260051020
     - `TIME_ENTRY` → entry.2044747982

6. 點選 Deploy 即可

如需協助可回來問我 👍
