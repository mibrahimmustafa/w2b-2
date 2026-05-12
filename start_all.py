import subprocess
import time
import sys
import os
import webbrowser

def run_scraper_system():
    print("🚀 W2B Scraper: Launching Full System...")
    
    # Paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_script = os.path.join(current_dir, "app", "main.py")
    frontend_dir = os.path.join(current_dir, "frontend")
    
    vector_db_script = os.path.join(current_dir, "vectorDB_API", "main.py")
    
    # 1. Start Backend
    print("📦 Starting FastAPI Backend (Port 8010)...")
    env = os.environ.copy()
    env["PYTHONPATH"] = current_dir
    env["PORT"] = "3010"
    backend_proc = subprocess.Popen([sys.executable, backend_script], env=env)
    
    # Wait for backend to start
    time.sleep(2)

    # 1.5 Start Vector DB API
    print("🧠 Starting Vector DB API (Port 8011)...")
    vectordb_proc = subprocess.Popen([sys.executable, vector_db_script], env=env)
    
    time.sleep(2)
    
    # 2. Start Frontend
    print("🎨 Starting Next.js Frontend (Port 3010)...")
    try:
        frontend_proc = subprocess.Popen("npm run dev", cwd=frontend_dir, env=env, shell=True)
    except FileNotFoundError:
        print("❌ Error: 'npm' not found. Please ensure Node.js is installed.")
        backend_proc.terminate()
        vectordb_proc.terminate()
        return

    print("\n✅ System Running!")
    print("👉 Dashboard: http://localhost:3010")
    print("👉 Scraper API Docs:  http://localhost:8010/docs")
    print("👉 Vector DB API Docs: http://localhost:8011/docs")
    print("\nPress Ctrl+C to stop all servers.")
    
    # Wait a few seconds for Next.js to start, then open the browser automatically
    time.sleep(3)
    webbrowser.open("http://localhost:3010")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping servers...")
        backend_proc.terminate()
        vectordb_proc.terminate()
        frontend_proc.terminate()
        print("Done.")

if __name__ == "__main__":
    run_scraper_system()
