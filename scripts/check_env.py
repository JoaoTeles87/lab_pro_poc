
import subprocess
import requests
import socket
import sys

def check_docker():
    print("Checking Docker...")
    try:
        subprocess.run(["docker", "ps"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ Docker is running.")
        return True
    except:
        print("❌ Docker is NOT reachable.")
        return False

def check_evolution():
    print("Checking Evolution API...")
    try:
        res = requests.get("http://localhost:8080/instance/fetchInstances", timeout=2)
        if res.status_code == 200:
            print("✅ Evolution API is responding.")
            return True
        else:
            print(f"❌ Evolution API returned status {res.status_code}.")
            return False
    except:
        print("❌ Evolution API is NOT reachable.")
        return False

def check_port_5001():
    print("Checking Port 5001 (App)...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(1)
        s.connect(('127.0.0.1', 5001))
        print("✅ Port 5001 is open (App is running).")
        s.close()
        return True
    except:
         print("⚠️ Port 5001 is closed (App is NOT running).")
         return False

if __name__ == "__main__":
    d = check_docker()
    e = check_evolution()
    a = check_port_5001()
    
    if d and e:
        print("\n🚀 Environment is ready!")
    else:
        print("\n❌ Environment is NOT ready. Please restart Docker.")
