# GenUI Engine 🚀

A modern, glassmorphic generative UI engine that turns prompts into professional, production-ready HTML components. Supports OpenAI, Google Gemini, and Local LLMs (Ollama/LM Studio).

## ✨ Key Features

- **Multi-Provider Support**: Switch between OpenAI (GPT-4o), Google Gemini (1.5 Pro), and Local LLMs effortlessly.
- **Persistent Server-Side History**: All generations are logged to `history.json` and saved as HTML files for instant restoration.
- **Glassmorphic Design**: A premium, modern UI powered by Tailwind CSS and Inter typography.
- **Interactive Iteration**: Every button in the generated UI acts as a new prompt context for the AI.
- **Dedicated Gemini App**: Optimized backend specifically for Gemini's OpenAI-compatible API.

## 🛠️ Getting Started

### 1. Prerequisites
- Python 3.8+
- [Optional] [Ollama](https://ollama.com/) or LM Studio for local LLM support.

### 2. Setup
Clone the repository and install dependencies:
```bash
pip install fastapi uvicorn openai pydantic
```

### 3. Running the Backends

#### For OpenAI / Local LLM (Port 8000)
```bash
python main.py
```

#### For Gemini (Port 8001)
```bash
python gemini_app.py
```

### 4. Opening the Frontend
Simply open `index.html` in your web browser.

## ⚙️ Configuration

- **Provider**: Choose your AI engine. The UI will auto-configure endpoints.
- **Backend URL**:
    - Port `8000` for `main.py`
    - Port `8001` for `gemini_app.py`
- **LLM Endpoint**:
    - **OpenAI**: (Default)
    - **Gemini**: `https://generativelanguage.googleapis.com/v1beta/`
    - **Local**: `http://localhost:11434/v1` (Ollama)

## 📁 Project Structure

- `index.html`: The main dashboard and preview area.
- `main.py`: Primary FastAPI backend for OpenAI and Local LLMs.
- `gemini_app.py`: Specialized backend for Google Gemini.
- `generated_logs/`: Directory where all your UI versions are stored.
- `history.json`: Metadata for your generation history.

## 🤝 Tips
- Use the **Refresh (🔄)** button next to the model field to instantly fetch available models from your LLM server.
- Click **+ New** to clear the current context and start a fresh design.
- Use the **History** sidebar to browse and restore previous versions of your UI.
