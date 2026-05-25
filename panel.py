#!/usr/bin/env python3
# Kindle 面板 v1 · 天气/PVE/路由器极速自适应版 · 标准库 only
import os
import json
import time
import ssl
import calendar
import threading
import urllib.request
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

# Force IPv4 only to bypass broken IPv6 DNS timeouts
import socket
orig_getaddrinfo = socket.getaddrinfo
def getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = getaddrinfo_ipv4

# ---------- 配置 ----------
LATITUDE = "31.86"
LONGITUDE = "117.28"
PORT = int(os.environ.get("PORT", "8088"))
WEATHER_REFRESH = int(os.environ.get("WEATHER_REFRESH_SECONDS", "1800"))

WEEKDAY_CN = ["一", "二", "三", "四", "五", "六", "日"]

WMO_CODES = {
    0: "晴",
    1: "晴", 2: "多云", 3: "阴",
    45: "大雾", 48: "大雾",
    51: "毛毛雨", 53: "毛毛雨", 55: "毛毛雨",
    56: "冻细雨", 57: "冻细雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    66: "冻雨", 67: "冻雨",
    71: "小雪", 73: "中雪", 75: "大雪",
    77: "雪粒",
    80: "阵雨", 81: "阵雨", 82: "阵雨",
    85: "阵雪", 86: "阵雪",
    95: "雷阵雨", 96: "雷阵雨伴雹", 99: "雷阵雨伴雹"
}

# ---------- 状态缓存 ----------
# 全局共享状态，带线程安全锁保护
state = {
    "now": None, 
    "daily": None, 
    "air": None, 
    "pve_rows": "<tr><td colspan='5'>正在获取系统状态...</td></tr>", 
    "fn_rows": "<tr><td colspan='2'>正在获取系统状态...</td></tr>", 
    "wifi_2g": "--",
    "wifi_5g": "--",
    "updated": "未获取", 
    "error": None
}
lock = threading.Lock()

def fetch_json(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": "kindle-panel/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def kmh_to_wind_scale(kmh):
    if kmh < 1: return "无风"
    elif kmh < 6: return "1级"
    elif kmh < 12: return "2级"
    elif kmh < 20: return "3级"
    elif kmh < 29: return "4级"
    elif kmh < 39: return "5级"
    elif kmh < 50: return "6级"
    elif kmh < 62: return "7级"
    elif kmh < 75: return "8级"
    else: return "大风"

def degree_to_direction(deg):
    directions = ["北风", "东北风", "东风", "东南风", "南风", "西南风", "西风", "西北风"]
    idx = int((deg + 22.5) % 360 / 45)
    return directions[idx]

def get_aqi_category(aqi):
    if aqi <= 50: return "优"
    elif aqi <= 100: return "良"
    elif aqi <= 150: return "轻度污染"
    elif aqi <= 200: return "中度污染"
    elif aqi <= 300: return "重度污染"
    else: return "严重污染"

# ---------- 局域网服务接口 (PVE & 路由器) ----------
pve_ticket = None
router_stok = None

def fetch_pve_status():
    global pve_ticket
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        # 1. 登录 PVE 获取 ticket (如已缓存则跳过)
        if not pve_ticket:
            login_url = "https://192.168.31.200:8006/api2/json/access/ticket"
            data = urllib.parse.urlencode({'username': 'root@pam', 'password': 'your_password'}).encode('utf-8')
            req = urllib.request.Request(login_url, data=data, method='POST')
            with urllib.request.urlopen(req, context=ctx, timeout=3) as r:
                resp = json.loads(r.read().decode('utf-8'))
                pve_ticket = resp['data']['ticket']
                
        # 2. 获取资源列表
        res_url = "https://192.168.31.200:8006/api2/json/cluster/resources"
        req_res = urllib.request.Request(res_url)
        req_res.add_header('Cookie', f'PVEAuthCookie={pve_ticket}')
        
        try:
            with urllib.request.urlopen(req_res, context=ctx, timeout=2) as r:
                resp_res = json.loads(r.read().decode('utf-8'))
                items = resp_res['data']
        except urllib.error.HTTPError as he:
            if he.code == 401:
                # Ticket 过期，重置并重试一次
                pve_ticket = None
                return fetch_pve_status()
            raise he
            
        # 3. 格式化为 HTML
        rows = []
        res_dict = {}
        for item in items:
            t = item.get('type')
            if t == 'node' and item.get('node') == 'pve':
                res_dict['pve'] = item
            elif t == 'qemu' and item.get('vmid') in [101, 102]:
                res_dict[item.get('vmid')] = item
                
        targets = [('pve', '主机 (pve)'), (101, '101 (fnos)'), (102, '102 (istoreos)')]
        for key, display_name in targets:
            item = res_dict.get(key)
            if not item:
                rows.append(f"<tr><td class='forecast-date'>{display_name}</td><td colspan='4'>未获取到数据</td></tr>")
                continue
                
            uptime_secs = item.get('uptime', 0)
            uptime_str = "--"
            if uptime_secs:
                days = uptime_secs // 86400
                hours = (uptime_secs % 86400) // 3600
                mins = (uptime_secs % 3600) // 60
                if days > 0:
                    uptime_str = f"{days}天 {hours:02d}:{mins:02d}"
                else:
                    uptime_str = f"{hours:02d}:{mins:02d}"
                    
            disk = item.get('disk', 0)
            maxdisk = item.get('maxdisk', 0)
            disk_pct = f"{disk / maxdisk * 100:.1f}%" if maxdisk else "0.0%"
            
            mem = item.get('mem', 0)
            maxmem = item.get('maxmem', 0)
            mem_pct = f"{mem / maxmem * 100:.1f}%" if maxmem else "0.0%"
            
            cpu = item.get('cpu', 0)
            cpu_pct = f"{cpu * 100:.1f}%" if cpu else "0.0%"
            
            rows.append(
                f"<tr>"
                f"<td class='forecast-date'>{display_name}</td>"
                f"<td>{disk_pct}</td>"
                f"<td>{mem_pct}</td>"
                f"<td>{cpu_pct}</td>"
                f"<td class='forecast-wind'>{uptime_str}</td>"
                f"</tr>"
            )
            
        return "\n".join(rows)
    except Exception as e:
        # 清除 ticket 确保下次重试
        pve_ticket = None
        return f"<tr><td class='forecast-date' colspan='5'>获取 PVE 状态失败: {str(e)}</td></tr>"

def fetch_router_status():
    global router_stok
    mac = "YOUR_ROUTER_MAC"
    password = "YOUR_ROUTER_PASSWORD"
    key = "a2ffa5c9be07488bbb04a3a47d3c5f6a"
    
    try:
        # 1. 登录路由器 (若无 stok 则请求)
        if not router_stok:
            def sha1(s):
                import hashlib
                return hashlib.sha1(s.encode('utf-8')).hexdigest()
            
            import random
            nonce = f"0_{mac}_{int(time.time())}_{random.randint(0, 10000)}"
            pwd_hash = sha1(nonce + sha1(password + key))
            
            login_url = "http://192.168.31.1/cgi-bin/luci/api/xqsystem/login"
            data = urllib.parse.urlencode({
                "username": "admin",
                "password": pwd_hash,
                "nonce": nonce,
                "logtype": "2"
            }).encode('utf-8')
            
            req = urllib.request.Request(login_url, data=data, method='POST')
            with urllib.request.urlopen(req, timeout=3) as r:
                resp = json.loads(r.read().decode('utf-8'))
                if resp.get('code') == 0:
                    router_stok = resp.get('token')
                else:
                    return {"2g": "--", "5g": "--"}
                    
        # 2. 请求设备连接列表
        url = f"http://192.168.31.1/cgi-bin/luci/;stok={router_stok}/api/misystem/devicelist"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as r:
            data = json.loads(r.read().decode('utf-8'))
            if data.get('code') != 0:
                # Token 失效，重置并重试一次
                router_stok = None
                return fetch_router_status()
                
            count_2g = 0
            count_5g = 0
            for dev in data.get('list', []):
                if dev.get('online') == 1:
                    t = dev.get('type')
                    if t == 1:
                        count_2g += 1
                    elif t == 2:
                        count_5g += 1
            return {"2g": str(count_2g), "5g": str(count_5g)}
    except Exception:
        router_stok = None
        return {"2g": "--", "5g": "--"}

# ---------- 飞牛 OS 本地性能指标采集 ----------
fn_prev_cpu_total = 0
fn_prev_cpu_idle = 0
fn_prev_net_time = 0
fn_prev_net_rx = 0
fn_prev_net_tx = 0
fn_prev_io_time = 0
fn_prev_io_read = 0
fn_prev_io_write = 0

def fn_format_speed(bytes_per_sec):
    if bytes_per_sec < 1024:
        return f"{bytes_per_sec:.1f} B/s"
    elif bytes_per_sec < 1024 * 1024:
        return f"{bytes_per_sec / 1024:.1f} KB/s"
    else:
        return f"{bytes_per_sec / 1024 / 1024:.1f} MB/s"

def fn_get_uptime():
    try:
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.readline().split()[0])
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        if days > 0:
            return f"{days}天 {hours}小时 {minutes}分"
        else:
            return f"{hours}小时 {minutes}分"
    except Exception:
        return "--"

def fn_get_cpu_usage():
    global fn_prev_cpu_total, fn_prev_cpu_idle
    try:
        with open("/proc/stat", "r") as f:
            line = f.readline()
        if not line.startswith("cpu"):
            return 0.0
        parts = [float(x) for x in line.split()[1:]]
        total = sum(parts)
        idle = parts[3] + parts[4]
        
        if fn_prev_cpu_total == 0:
            fn_prev_cpu_total = total
            fn_prev_cpu_idle = idle
            return 0.0
            
        total_delta = total - fn_prev_cpu_total
        idle_delta = idle - fn_prev_cpu_idle
        
        fn_prev_cpu_total = total
        fn_prev_cpu_idle = idle
        
        if total_delta <= 0:
            return 0.0
        return (1.0 - idle_delta / total_delta) * 100
    except Exception:
        return 0.0

def fn_get_mem_usage():
    try:
        mem_total = 0
        mem_avail = 0
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    mem_total = int(line.split()[1])
                elif line.startswith("MemAvailable:"):
                    mem_avail = int(line.split()[1])
        if mem_total == 0:
            return "--", "--"
        used = mem_total - mem_avail
        used_gb = used / 1024 / 1024
        pct = (used / mem_total) * 100
        return f"{used_gb:.2f} GB", f"{pct:.1f}%"
    except Exception:
        return "--", "--"

def fn_get_net_speed():
    global fn_prev_net_time, fn_prev_net_rx, fn_prev_net_tx
    try:
        now_time = time.time()
        rx_bytes = 0
        tx_bytes = 0
        with open("/proc/net/dev", "r") as f:
            lines = f.readlines()
        for line in lines[2:]:
            parts = line.split()
            if len(parts) < 17:
                continue
            iface = parts[0].strip(":")
            if iface == "lo" or iface.startswith("veth") or iface.startswith("docker") or iface.startswith("br-"):
                continue
            rx_bytes += int(parts[1])
            tx_bytes += int(parts[9])
            
        if fn_prev_net_time == 0:
            fn_prev_net_time = now_time
            fn_prev_net_rx = rx_bytes
            fn_prev_net_tx = tx_bytes
            return 0.0, 0.0
            
        dt = now_time - fn_prev_net_time
        if dt <= 0:
            dt = 1.0
            
        rx_speed = (rx_bytes - fn_prev_net_rx) / dt
        tx_speed = (tx_bytes - fn_prev_net_tx) / dt
        
        fn_prev_net_time = now_time
        fn_prev_net_rx = rx_bytes
        fn_prev_net_tx = tx_bytes
        
        return rx_speed, tx_speed
    except Exception:
        return 0.0, 0.0

def fn_get_disk_speed():
    global fn_prev_io_time, fn_prev_io_read, fn_prev_io_write
    try:
        now_time = time.time()
        read_sectors = 0
        write_sectors = 0
        with open("/proc/diskstats", "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 14:
                    continue
                dev = parts[2]
                is_disk = False
                if dev.startswith("sd") and not dev[-1].isdigit():
                    is_disk = True
                elif dev.startswith("vd") and not dev[-1].isdigit():
                    is_disk = True
                elif dev.startswith("nvme") and "p" not in dev:
                    is_disk = True
                if is_disk:
                    read_sectors += int(parts[5])
                    write_sectors += int(parts[9])
                    
        read_bytes = read_sectors * 512
        write_bytes = write_sectors * 512
        
        if fn_prev_io_time == 0:
            fn_prev_io_time = now_time
            fn_prev_io_read = read_bytes
            fn_prev_io_write = write_bytes
            return 0.0, 0.0
            
        dt = now_time - fn_prev_io_time
        if dt <= 0:
            dt = 1.0
            
        r_speed = (read_bytes - fn_prev_io_read) / dt
        w_speed = (write_bytes - fn_prev_io_write) / dt
        
        fn_prev_io_time = now_time
        fn_prev_io_read = read_bytes
        fn_prev_io_write = write_bytes
        
        return r_speed, w_speed
    except Exception:
        return 0.0, 0.0

def fetch_fnos_status_html():
    uptime_str = fn_get_uptime()
    cpu_usage = fn_get_cpu_usage()
    mem_used, mem_pct = fn_get_mem_usage()
    rx, tx = fn_get_net_speed()
    disk_r, disk_w = fn_get_disk_speed()
    
    import socket
    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = "fnos"
        
    metrics = [
        ("系统说明", f"飞牛 OS ({hostname})"),
        ("运行时间", uptime_str),
        ("CPU 利用率", f"{cpu_usage:.1f}%"),
        ("内存已用", f"{mem_used} ({mem_pct})"),
        ("网络上行", f"↑ {fn_format_speed(tx)}"),
        ("网络下行", f"↓ {fn_format_speed(rx)}"),
        ("硬盘速度", f"读 {fn_format_speed(disk_r)} · 写 {fn_format_speed(disk_w)}"),
    ]
    
    rows = []
    for label, val in metrics:
        rows.append(
            f"<tr>"
            f"<td class='forecast-date'>{label}</td>"
            f"<td class='forecast-wind'>{val}</td>"
            f"</tr>"
        )
    return "\n".join(rows)

# ---------- 定时轮询线程 ----------
def weather_refresh_loop():
    while True:
        try:
            # 1. 抓取外部天气
            weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={LATITUDE}&longitude={LONGITUDE}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m&daily=weather_code,temperature_2m_max,temperature_2m_min,wind_speed_10m_max,wind_direction_10m_dominant&timezone=Asia/Shanghai"
            w_data = fetch_json(weather_url)
            
            # 2. 抓取外网空气质量
            aqi_url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={LATITUDE}&longitude={LONGITUDE}&current=us_aqi&timezone=Asia/Shanghai"
            aqi_data = None
            try:
                aqi_data = fetch_json(aqi_url)
            except Exception:
                pass
                
            with lock:
                state["now"] = w_data.get("current")
                state["daily"] = w_data.get("daily")
                state["air"] = aqi_data.get("current") if aqi_data else None
                state["updated"] = datetime.now().strftime("%H:%M")
                state["error"] = None
        except Exception as e:
            with lock:
                state["error"] = "获取外网天气数据失败：" + str(e)
        time.sleep(WEATHER_REFRESH)

def local_status_refresh_loop():
    pve_counter = 0
    router_counter = 0
    while True:
        # PVE & 飞牛状态：每 1 秒在后台抓取更新一次
        if pve_counter >= 1:
            pve_html = fetch_pve_status()
            fn_html = fetch_fnos_status_html()
            with lock:
                state["pve_rows"] = pve_html
                state["fn_rows"] = fn_html
            pve_counter = 0
            
        # 路由器设备数量：每 5 秒在后台抓取更新一次
        if router_counter >= 5:
            r_data = fetch_router_status()
            with lock:
                state["wifi_2g"] = r_data.get("2g", "--")
                state["wifi_5g"] = r_data.get("5g", "--")
            router_counter = 0
            
        time.sleep(1)
        pve_counter += 1
        router_counter += 1

def render_daily(daily):
    if not daily:
        return "<tr><td colspan='3'>暂无预报数据</td></tr>"
    out = ""
    times = daily.get("time", [])
    codes = daily.get("weather_code", [])
    t_maxs = daily.get("temperature_2m_max", [])
    t_mins = daily.get("temperature_2m_min", [])
    
    for i in range(min(7, len(times))):
        try:
            dd = datetime.strptime(times[i], "%Y-%m-%d")
            if i == 0:
                label = "今天"
            elif i == 1:
                label = "明天"
            else:
                label = "周" + WEEKDAY_CN[dd.weekday()]
            short = dd.strftime("%m.%d")
        except Exception:
            label = ""
            short = times[i]
            
        code = codes[i] if i < len(codes) else 0
        weather_text = WMO_CODES.get(code, "未知")
        t_max = t_maxs[i] if i < len(t_maxs) else "--"
        t_min = t_mins[i] if i < len(t_mins) else "--"
        
        out += ("<tr>"
                + "<td class='forecast-date'>" + label + "<br><span class='sub'>" + short + "</span></td>"
                + "<td>" + weather_text + "</td>"
                + "<td class='forecast-wind'>" + str(t_min) + "° <span class='sub'>/ " + str(t_max) + "°</span></td>"
                + "</tr>")
    return out

HTML = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="300">
<title>Kindle Weather & PVE Dashboard</title>
<style>
    body {
      background-color: #ffffff;
      color: #000000;
      font-family: "Helvetica Neue", Helvetica, Arial, "PingFang SC", "Hiragino Sans GB", "Heiti SC", "Microsoft YaHei", sans-serif;
      -webkit-font-smoothing: none;
      padding: 16px;
      margin: 0 auto;
      max-width: 800px;
    }
    
    table {
      width: 100%;
      border-collapse: collapse;
    }
    
    /* Header layout using clean Table instead of Flexbox */
    .header-table {
      width: 100%;
      border-bottom: 2px solid #000000;
      padding-bottom: 8px;
      margin-bottom: 16px;
    }
    .header-table td {
      border: none;
      padding: 0;
      vertical-align: bottom;
    }
    .header-date {
      font-size: 26px;
      font-weight: bold;
      letter-spacing: -0.5px;
    }
    .header-sub {
      font-size: 16px;
      font-weight: bold;
      margin-top: 4px;
    }
    .header-time {
      font-size: 52px;
      font-weight: bold;
      text-align: right;
      letter-spacing: -2px;
      line-height: 1.0;
    }

    /* Kindle Section Border styling */
    .kindle-section {
      border: 2px solid #000000;
      margin-bottom: 20px;
    }
    .section-title {
      background-color: #000000;
      color: #ffffff;
      padding: 4px 12px;
      font-size: 16px;
      font-weight: bold;
      letter-spacing: 1px;
    }
    
    /* Current Weather Table Layout */
    .cur-table {
      width: 100%;
    }
    .cur-table td {
      padding: 16px;
      vertical-align: middle;
    }
    .cur-temp-cell {
      width: 40%;
      font-size: 72px;
      font-weight: bold;
      text-align: center;
      border-right: 2px solid #000000;
      letter-spacing: -3px;
    }
    .cur-details-cell {
      padding-left: 24px !important;
    }
    .cur-title-row {
      font-size: 28px;
      font-weight: bold;
      border-bottom: 2px solid #000000;
      padding-bottom: 6px;
      margin-bottom: 8px;
    }
    .cur-title-sub {
      font-size: 18px;
      font-weight: normal;
    }
    .cur-sub-row {
      font-size: 16px;
      margin-top: 8px;
    }

    /* Forecast Table Layout */
    .forecast-table {
      width: 100%;
    }
    .forecast-table th, .forecast-table td {
      border-bottom: 2px solid #000000;
      padding: 10px 16px;
      font-size: 16px;
      text-align: center;
      vertical-align: middle;
    }
    .forecast-table th {
      background-color: #eeeeee;
      font-weight: bold;
      font-size: 14px;
    }
    .forecast-table tr:last-child td {
      border-bottom: none;
    }
    .forecast-date {
      font-size: 18px;
      font-weight: bold;
      text-align: left !important;
    }
    .forecast-date .sub {
      font-size: 12px;
      font-weight: normal;
      color: #333333;
    }
    .forecast-temp {
      font-size: 18px;
      font-weight: bold;
    }
    .forecast-temp .sub {
      font-size: 16px;
      font-weight: normal;
    }
    .forecast-wind {
      text-align: right !important;
    }
    
    .foot {
      margin-top: 16px;
      font-size: 11px;
      color: #555555;
      text-align: center;
    }
    
    .err {
      border: 2px solid #000000;
      background-color: #000000;
      color: #ffffff;
      padding: 8px 12px;
      margin-bottom: 16px;
      font-size: 14px;
      font-weight: bold;
    }
</style>
</head>
<body>
<table class="header-table">
  <tr>
    <td>
      <div class="header-date">__DATE__</div>
      <div class="header-sub">__WEEKDAY__ · 合肥包河 · 📶 2.4G: __WIFI_2G__台 / 5G: __WIFI_5G__台</div>
    </td>
    <td class="header-time">__TIME__</td>
  </tr>
</table>

__ERROR_BLOCK__

<div class="kindle-section">
  <div class="section-title">当前天气</div>
  <table class="cur-table">
    <tr>
      <td class="cur-temp-cell">__TEMP__°</td>
      <td class="cur-details-cell">
        <div class="cur-title-row">__TEXT__ <span class="cur-title-sub">· 体感 __FEELS__°</span></div>
        <div class="cur-sub-row">湿度 __HUMID__% · __WIND__ · 空气 __AQI__ __AQI_CAT__</div>
      </td>
    </tr>
  </table>
</div>

<table style="width:100%; table-layout:fixed; border-collapse:collapse; border-spacing:0; margin-bottom:20px;">
  <tr>
    <td style="width:49%; vertical-align:top; padding:0;">
      <div class="kindle-section" style="margin-bottom:0;">
        <div class="section-title">未来 7 天</div>
        <table class="forecast-table">
          __DAILY_ROWS__
        </table>
      </div>
    </td>
    <td style="width:2%;"></td>
    <td style="width:49%; vertical-align:top; padding:0;">
      <div class="kindle-section" style="margin-bottom:0;">
        <div class="section-title">飞牛 OS 运行状态</div>
        <table class="forecast-table">
          __FN_ROWS__
        </table>
      </div>
    </td>
  </tr>
</table>

<div class="kindle-section">
  <div class="section-title">系统状态 (PVE & 虚拟机) - 秒级实时</div>
  <table class="forecast-table">
    <tr>
      <th style="text-align:left;">说明</th>
      <th>磁盘使用率</th>
      <th>内存使用率</th>
      <th>CPU 利用率</th>
      <th style="text-align:right;">运行时间</th>
    </tr>
    __PVE_ROWS__
  </table>
</div>

<div class="foot">数据更新 __UPDATED__ · 页面每 5 分钟自动刷新 · 数据来源 Open-Meteo & PVE & MiWiFi</div>
</body>
</html>"""

def render_page():
    now_dt = datetime.now()
    weekday_cn = WEEKDAY_CN[now_dt.weekday()]
    with lock:
        s_now = state["now"]
        s_daily = state["daily"]
        s_air = state["air"]
        pve_rows = state["pve_rows"]
        fn_rows = state["fn_rows"]
        wifi_2g = state["wifi_2g"]
        wifi_5g = state["wifi_5g"]
        s_updated = state["updated"] or "未获取"
        s_error = state["error"]

    if s_now:
        cur_temp = s_now.get("temperature_2m", "--")
        code = s_now.get("weather_code", 0)
        cur_text = WMO_CODES.get(code, "未知")
        cur_humid = s_now.get("relative_humidity_2m", "--")
        cur_feels = s_now.get("apparent_temperature", "--")
        
        w_speed = s_now.get("wind_speed_10m", 0)
        w_dir = s_now.get("wind_direction_10m", 0)
        cur_wind = f"{degree_to_direction(w_dir)} {kmh_to_wind_scale(w_speed)}"
    else:
        cur_temp = cur_text = cur_humid = cur_feels = "--"
        cur_wind = "--"

    if s_air:
        aqi = int(s_air.get("us_aqi", 0))
        aqi_cat = get_aqi_category(aqi)
    else:
        aqi = "--"
        aqi_cat = ""

    daily_rows = render_daily(s_daily) if s_daily else "<tr><td colspan='3'>预报数据未加载</td></tr>"
    err_block = ""
    if s_error:
        err_block = '<div class="err">数据异常：' + s_error + "</div>"

    html = (HTML
        .replace("__DATE__", now_dt.strftime("%Y年%m月%d日"))
        .replace("__WEEKDAY__", "星期" + weekday_cn)
        .replace("__TIME__", now_dt.strftime("%H:%M"))
        .replace("__TEMP__", str(cur_temp))
        .replace("__TEXT__", str(cur_text))
        .replace("__HUMID__", str(cur_humid))
        .replace("__FEELS__", str(cur_feels))
        .replace("__WIND__", str(cur_wind))
        .replace("__AQI__", str(aqi))
        .replace("__AQI_CAT__", str(aqi_cat))
        .replace("__DAILY_ROWS__", daily_rows)
        .replace("__FN_ROWS__", fn_rows)
        .replace("__PVE_ROWS__", pve_rows)
        .replace("__WIFI_2G__", str(wifi_2g))
        .replace("__WIFI_5G__", str(wifi_5g))
        .replace("__UPDATED__", s_updated)
        .replace("__ERROR_BLOCK__", err_block))
    return html

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = render_page().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.header_time = None
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, fmt, *args):
        print(self.address_string(), self.command, self.path)

if __name__ == "__main__":
    # 开启外网天气轮询线程 (30 分钟刷新一次)
    t_weather = threading.Thread(target=weather_refresh_loop, daemon=True)
    t_weather.start()
    
    # 开启局域网高频状态轮询线程 (PVE 每 1 秒, 路由器每 5 秒)
    t_local = threading.Thread(target=local_status_refresh_loop, daemon=True)
    t_local.start()
    
    print("Kindle 面板 v1 启动：http://0.0.0.0:" + str(PORT) + "/")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
