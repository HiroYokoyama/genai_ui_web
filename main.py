import os
import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from openai import AsyncOpenAI

app = FastAPI(title="Generative UI Engine")

# 保存用ディレクトリ
LOG_DIR = "generated_logs"
HISTORY_FILE = os.path.join(LOG_DIR, "history.json")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        import json
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_history(entry):
    import json
    history = load_history()
    history.insert(0, entry) # 最新を上へ
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history[:100], f, ensure_ascii=False, indent=2) # 直近100件

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/logs", StaticFiles(directory="generated_logs"), name="logs")

class UIRequest(BaseModel):
    current_html: str
    user_action: str
    api_key: str
    system_prompt: str = ""
    llm_url: str = ""
    model: str = "gpt-4o"

@app.get("/")
async def read_index():
    return FileResponse("index.html")

@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "GenUI Server is running"}

@app.get("/history")
async def get_history():
    return load_history()

@app.get("/models")
async def get_models(llm_url: str = "", api_key: str = ""):
    if not llm_url and not api_key:
        raise HTTPException(status_code=400, detail="LLM URL or API Key is required.")
    
    # URLの補正 (schemeがない、または typo への対応)
    if llm_url:
        if not llm_url.startswith("http"):
            llm_url = "http://" + llm_url
        # ユーザーの入力ミス (ttps 等) への簡易的な対応
        if llm_url.startswith("ttp"):
            llm_url = "h" + llm_url
        
        # Google API URL の場合は /openai/ が含まれているかチェック
        if "generativelanguage.googleapis.com" in llm_url and "/openai/" not in llm_url:
            if not llm_url.endswith("/"):
                llm_url += "/"
            llm_url += "openai/"
            print(f"Corrected Gemini URL to: {llm_url}")

    client_args = {"api_key": api_key}
    if llm_url:
        client_args["base_url"] = llm_url
        
    try:
        client = AsyncOpenAI(**client_args)
        response = await client.models.list()
        return {"models": [m.id for m in response.data]}
    except Exception as e:
        error_msg = str(e)
        print(f"Error fetching models: {error_msg}")
        # URL関連のエラーなら詳細を返す
        if "base_url" in error_msg or "URL" in error_msg or "404" in error_msg:
            raise HTTPException(status_code=400, detail=f"Invalid LLM URL (Did you include /openai/ for Gemini?): {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/generate")
async def generate_ui(req: UIRequest):
    if not req.api_key and not req.llm_url:
        raise HTTPException(status_code=400, detail="API Key or Local LLM URL is required.")

    # LLM URLが提供されている場合はそれを使用し、そうでなければOpenAIのデフォルトを使用
    client_args = {"api_key": req.api_key}
    if req.llm_url:
        client_args["base_url"] = req.llm_url
    
    client = AsyncOpenAI(**client_args)

    # 開発者によって調整された高度なシステムプロンプト
    DEFAULT_SYSTEM_PROMPT = """
    You are an expert Senior UI/UX Engineer specialized in modern SaaS dashboards and web applications.
    Your goal is to generate extremely high-quality, professional, and visually stunning HTML components using Tailwind CSS.

    [STRICT OUTPUT RULES]
    1. Return ONLY raw HTML code. 
    2. NO markdown formatting (DO NOT use ```html or ```).
    3. NO explanation or conversational text.
    4. Use Tailwind CSS for all styling. Use vibrant colors, glassmorphism, and modern shadows.
    5. The UI must be responsive and feel "alive" (hover effects, smooth transitions).
    6. All interactive elements (buttons, links) should look clickable but DO NOT include custom JavaScript functions or `onclick` handlers.
    7. If the user interaction says "User pushed [Button Name] button", interpret this as a navigation or state change request and generate the corresponding NEXT screen.
    """

    system_prompt = req.system_prompt if req.system_prompt else DEFAULT_SYSTEM_PROMPT

    user_prompt = f"""
    [User Action/Intent]: {req.user_action}
    
    [Current HTML Context]:
    ```html
    {req.current_html[:5000]}
    ```
    
    Update the UI based on the user's action. Maintain consistent branding and layout.
    """

    try:
        response = await client.chat.completions.create(
            model=req.model if req.model else "gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.4,
        )
        
        generated_html = response.choices[0].message.content.strip()
        
        # クリーンアップ
        generated_html = generated_html.replace("```html", "").replace("```", "").strip()

        # --- ログ保存 & 履歴追加処理 ---
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        file_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ui_{file_timestamp}.html"
        filepath = os.path.join(LOG_DIR, filename)

        # ファイル保存
        with open(filepath, "w", encoding="utf-8") as f:
            log_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>body {{ font-family: 'Inter', sans-serif; }}</style>
</head>
<body class="p-10 bg-slate-50">
    {generated_html}
</body>
</html>
"""
            f.write(log_content)
        
        # 履歴 JSON に保存
        save_history({
            "intent": req.user_action,
            "filename": filename,
            "time": timestamp,
            "model": req.model
        })

        print(f"[{timestamp}] Generated & Logged: {filename}")

        return {"html": generated_html}

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
