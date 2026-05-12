import subprocess
import sys

def kill_process_on_port_windows(port):
    """Finds and kills the process listening on the specified port (Windows)."""
    try:
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.strip().split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    if pid != "0":
                        print(f"🛑 Found process {pid} on port {port}. Killing it...")
                        subprocess.run(['taskkill', '/F', '/T', '/PID', pid], capture_output=True)
                        print(f"✅ Process {pid} and its children killed.")
                        return True
        print(f"ℹ️ No process found listening on port {port}.")
        return False
    except Exception as e:
        print(f"❌ Error killing process on port {port}: {e}")
        return False

def kill_process_on_port_linux(port):
    """Finds and kills the process listening on the specified port (Linux/Mac)."""
    try:
        # Try using lsof first
        result = subprocess.run(['lsof', '-t', f'-i:{port}'], capture_output=True, text=True)
        pids = result.stdout.strip().split('\n')
        
        killed_any = False
        for pid in pids:
            if pid:
                print(f"🛑 Found process {pid} on port {port}. Killing it...")
                subprocess.run(['kill', '-9', pid], capture_output=True)
                print(f"✅ Process {pid} killed.")
                killed_any = True
                
        if not killed_any:
            # If no output from lsof, it might not be running or not found
            pass
        else:
            return True
            
    except FileNotFoundError:
        pass # Fall through to trying fuser
    except Exception as e:
        print(f"❌ Error using lsof on port {port}: {e}")
    
    # Try using fuser if lsof fails or is not installed
    try:
        result = subprocess.run(['fuser', '-k', f'{port}/tcp'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Process on port {port} killed using fuser.")
            return True
    except FileNotFoundError:
        print(f"❌ Neither 'lsof' nor 'fuser' commands were found. Please install them to stop processes by port.")
    except Exception as e:
        print(f"❌ Error using fuser on port {port}: {e}")
        
    print(f"ℹ️ No process found listening on port {port}.")
    return False

def kill_process_on_port(port):
    if sys.platform == "win32":
        return kill_process_on_port_windows(port)
    else:
        return kill_process_on_port_linux(port)

def stop_all():
    print("🛑 W2B Scraper: Stopping Full System...\n")
    
    ports_to_kill = [
        ("FastAPI Backend", 8010),
        ("Vector DB API", 8011),
        ("Next.js Frontend", 3010)
    ]
    
    for name, port in ports_to_kill:
        print(f"Checking {name} (Port {port})...")
        kill_process_on_port(port)
        print("-" * 30)
        
    print("\n✅ All specified servers have been stopped!")

if __name__ == "__main__":
    stop_all()
