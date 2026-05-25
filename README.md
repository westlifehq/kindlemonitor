# Kindle 极简天气日历面板 (Kindle Weather & Calendar Dashboard)

这是一个专为旧版 Kindle 体验版浏览器定制的**极简、超高对比度天气与日历看板系统**。本系统采用零外部依赖架构，专为电子墨水屏 (E-Ink) 进行像素级优化，支持在低性能嵌入式浏览器上完美对齐并展示。

---

## 🎨 界面展示与特点

* **极致兼容性**：弃用现代浏览器常用的 Flexbox/Grid 布局，全面采用高鲁棒性的标准 HTML `<table>` 网格渲染，确保在 Kindle 极简/体验版浏览器上完美对齐，绝对不发生移位或空白。
* **墨水屏防重影模糊**：CSS 内置 `-webkit-font-smoothing: none;`，强制关闭文字抗锯齿，使边缘在 E-Ink 屏幕上高度锐利清晰，防止发虚。
* **零配置/免 Key 天气体系**：完全换用 **Open-Meteo 开源公益气象数据源**（包含 Weather API 与 Air Quality API），无需注册、无需获取 API Key、完全免费且无限额度。
* **极致性能与轻量**：基于 Python 原生标准库实现 (零第三方库依赖)，运行内存占用仅约 `11-12MB`，对主系统几乎零负载。
* **系统级容灾自愈**：提供 `systemd` 配置，支持开机自动后台拉起，并具备进程意外崩溃 5 秒内自动重启恢复的自愈能力。
* **自动轮询刷新**：前台配置 `5分钟` 自动 Meta 刷新，Kindle 挂置常亮即可实现自动跳秒更新。

---

## 🛠️ 项目结构

```text
├── panel.py               # 面板服务端主程序 (内置多线程异步缓存 + HTTP 服务器)
├── kindle-panel.service   # Linux systemd 服务配置文件
├── ssh_run.py             # 基于 pexpect 封装的 SSH 免密指令代理脚本
├── scp_put.py             # 基于 pexpect 封装的 SCP 文件传输代理脚本
├── run.sh                 # 本地 IDE 终端执行静默代理脚本
├── README.md              # 项目使用说明文档
└── CHANGELOG.md           # 项目更新日志
```

---

## 🚀 部署指南 (以飞牛 OS / 经典 Debian 系统为例)

### Step 1: 准备目录与配置文件
在宿主机上建立项目工作空间：
```bash
mkdir -p /vol1/@appdata/kindle-panel
```
在 `/vol1/@appdata/kindle-panel/.env` 写入基础环境变量配置：
```ini
PORT=8088
WEATHER_REFRESH_SECONDS=1800
```

### Step 2: 传输并部署代码
将 `panel.py` 传输至目标宿主机 `/vol1/@appdata/kindle-panel/panel.py`，并授予执行权限：
```bash
chmod +x /vol1/@appdata/kindle-panel/panel.py
```

### Step 3: 配置并启动系统服务
1. 将 `kindle-panel.service` 移动至系统服务目录：
   ```bash
   sudo cp kindle-panel.service /etc/systemd/system/kindle-panel.service
   ```
2. 重载 systemd 并启动服务：
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now kindle-panel.service
   ```
3. 查看服务状态以确保正常运行：
   ```bash
   sudo systemctl status kindle-panel.service
   ```

### Step 4: 局域网防火墙放行
若宿主机配置有防火墙限制，请放行 `8088` 端口入站规则：
```bash
sudo iptables -I INPUT -p tcp --dport 8088 -j ACCEPT
```

---

## 🔍 技术解析与避坑指南

### 1. IPv6 DNS 解析超时挂起问题 (必看 ⚠️)
许多家庭宽带/路由器会自动下发损坏或超时的链路本地 IPv6 DNS 服务器 (`fe80::...`)。这会导致 Python 标准库 `urllib.request` 默认优先解析 IPv6 时发生持续死锁，直到触发 `read operation timed out` 报错。

本项目在 `panel.py` 顶部内置了一行**强制 IPv4 解析猴子补丁 (Monkeypatch)**：
```python
import socket
orig_getaddrinfo = socket.getaddrinfo
def getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = getaddrinfo_ipv4
```
该补丁无缝拦截所有 DNS 请求并强制仅走 IPv4 解析，请求处理速度缩短至 **0.5秒内**。

---

## 📄 开源协议

本项目基于 MIT License 协议开源。
