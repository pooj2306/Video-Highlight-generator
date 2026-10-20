# How to Run in Visual Studio Code (VS Code)

You do **not** need Antigravity open to run this project. You can run and develop it completely inside **VS Code** or from Windows Explorer.

---

### Method 1: Press `F5` in VS Code (Easiest)
1. Open this folder in VS Code (`File` → `Open Folder...`).
2. Press **`F5`** (or go to `Run` → `Start Debugging`).
3. Select **`FastAPI: Web Application (Uvicorn)`**.
4. The server starts and is ready at **http://127.0.0.1:8000**.

---

### Method 2: One-Click Script (`run.bat`)
- In Windows Explorer or in the VS Code file tree, simply **double-click `run.bat`** (or type `.\run.bat` in the VS Code terminal).
- It will automatically launch the server and open **http://127.0.0.1:8000** in your browser.

---

### Method 3: VS Code Built-in Task (`Ctrl+Shift+B`)
1. Press **`Ctrl + Shift + B`** (or `Terminal` → `Run Build Task...`).
2. Select **`Start Web Server (Uvicorn)`**.
3. It will run in the background terminal.

---

### Method 4: Terminal Command
Open a terminal in VS Code (`Ctrl + \``) and run:
```powershell
.\venv\Scripts\python -m uvicorn app.server:app --port 8000 --reload --reload-dir app --reload-dir src
```
or simply:
```powershell
python start.py
```

---

## About the Groq API Key & Offline Mode

1. **Running 100% Offline (No Key Needed)**:
   - On the web page, select **"On this machine"** under *Transcription*.
   - The app will transcribe using local Whisper and score clips offline with audio, scene cut, and speech density heuristics. No internet connection or API key is required.

2. **Using Groq API**:
   - If you have a free Groq key from [console.groq.com/keys](https://console.groq.com/keys):
   - You can enter it directly in the web app by clicking the **"Groq API Key"** button in the top right header, or by placing `GROQ_API_KEY=gsk_...` in your `.env` file.
