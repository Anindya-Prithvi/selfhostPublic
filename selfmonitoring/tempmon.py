import http.server
import socketserver
import threading
import time
import os
import subprocess

# --- Configuration ---
TEMP_FILE = "/sys/class/thermal/thermal_zone0/temp"

TEMP_LOG = "temp_log.csv"
PING_LOG = "ping_log.csv"

PING_HOST = "ola.com"
PING_COUNT = 4

INTERVAL = 300
MAX_SIZE_MB = 15 
PORT = 18001


def trim_file(file):
    if os.path.exists(file) and os.path.getsize(file) > MAX_SIZE_MB * 1024 * 1024:
        with open(file, "r") as f:
            lines = f.readlines()
        with open(file, "w") as f:
            f.writelines(lines[len(lines)//5:])


# ---------- TEMP ----------
def get_temp():
    try:
        with open(TEMP_FILE, "r") as f:
            return int(f.read().strip()) / 1000.0
    except:
        return 0.0


def log_temperature():
    while True:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        temp = get_temp()

        with open(TEMP_LOG, "a") as f:
            f.write(f"{timestamp},{temp}\n")

        trim_file(TEMP_LOG)
        time.sleep(INTERVAL)


# ---------- PING ----------
def get_ping():
    try:
        cmd = ["ping", "-c", str(PING_COUNT), "-W", "1", PING_HOST]
        result = subprocess.run(cmd, capture_output=True, text=True)

        for line in result.stdout.split("\n"):
            if "rtt min/avg/max/mdev" in line:
                stats = line.split("=")[1].split("ms")[0].strip()
                return stats.split("/")
    except:
        pass

    return [0, 0, 0, 0]


def log_ping():
    while True:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        min_rtt, avg_rtt, max_rtt, mdev = get_ping()

        with open(PING_LOG, "a") as f:
            f.write(f"{timestamp},{min_rtt},{avg_rtt},{max_rtt},{mdev}\n")

        trim_file(PING_LOG)
        time.sleep(INTERVAL)


# ---------- HTTP SERVER ----------
import signal

httpd = None

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def run_server():
    global httpd

    handler = http.server.SimpleHTTPRequestHandler
    httpd = ReusableTCPServer(("", PORT), handler)

    print(f"Server active at http://localhost:{PORT}")

    def shutdown_server(signum, frame):
        print("\nShutting down server...")
        httpd.shutdown()      # stop serve_forever loop
        httpd.server_close()  # close socket
        print("Server stopped cleanly")
        os._exit(0)

    signal.signal(signal.SIGINT, shutdown_server)   # Ctrl+C
    signal.signal(signal.SIGTERM, shutdown_server)  # kill

    httpd.serve_forever()

if __name__ == "__main__":

    if not os.path.exists(TEMP_LOG):
        with open(TEMP_LOG, "w") as f:
            f.write("timestamp,temp\n")

    if not os.path.exists(PING_LOG):
        with open(PING_LOG, "w") as f:
            f.write("timestamp,min,avg,max,mdev\n")

    threading.Thread(target=log_temperature, daemon=True).start()
    threading.Thread(target=log_ping, daemon=True).start()

    run_server()
