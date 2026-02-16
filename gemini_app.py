import os
import datetime
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from openai import AsyncOpenAI

app = FastAPI(title="GenUI Engine - Gemini Edition")

# 保存用ディレクトリ
LOG_DIR = "generated_logs"
HISTORY_FILE = os.path.join(LOG_DIR, "history.json")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_history(entry):
    history = load_history()
    history.insert(0, entry)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history[:100], f, ensure_ascii=False, indent=2)

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
    # Gemini Default Endpoint
    llm_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    model: str = "gemini-1.5-pro-latest"

@app.get("/")
async def read_index():
    return FileResponse("index.html")

@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "GenUI Gemini Server is running"}

@app.get("/history")
async def get_history():
    return load_history()

@app.get("/models")
async def get_models(llm_url: str = "", api_key: str = ""):
    if not llm_url and not api_key:
        raise HTTPException(status_code=400, detail="LLM URL or API Key is required.")
    
    # URL 補正
    if llm_url:
        if not llm_url.startswith("http"):
            llm_url = "http://" + llm_url
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
    if not req.api_key:
        raise HTTPException(status_code=400, detail="Gemini API Key is required.")

    # Gemini API (OpenAI Compatible)
    client = AsyncOpenAI(
        api_key=req.api_key,
        base_url=req.llm_url
    )

    DEFAULT_SYSTEM_PROMPT = """
    You are an expert Senior UI/UX Engineer specialized in modern SaaS dashboards and web applications.
    Your goal is to generate extremely high-quality, professional, and visually stunning HTML components using Tailwind CSS.
    Use vibrant colors, glassmorphism, and modern shadows.
    
    [STRICT OUTPUT RULES]
    1. Return ONLY raw HTML code. 
    2. NO markdown formatting.
    3. NO explanation.
    """

    system_prompt = req.system_prompt if req.system_prompt else DEFAULT_SYSTEM_PROMPT

    user_prompt = f"""
    [User Action/Intent]: {req.user_action}
    [Current HTML Context]:
    {req.current_html[:5000]}
    
    Update the UI based on the user's action.
    """

    try:
        response = await client.chat.completions.create(
            model=req.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.4,
        )
        
        generated_html = response.choices[0].message.content.strip()
        generated_html = generated_html.replace("```html", "").replace("```", "").strip()

        # Save & Log
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        file_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ui_{file_timestamp}.html"
        filepath = os.path.join(LOG_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"<!DOCTYPE html><html><head><script src='https://cdn.tailwindcss.com'></script></head><body>{generated_html}</body></html>")
        
        save_history({
            "intent": req.user_action,
            "filename": filename,
            "time": timestamp,
            "model": req.model
        })

        return {"html": generated_html}

    except Exception as e:
        print(f"Gemini Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
