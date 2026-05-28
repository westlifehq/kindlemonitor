# Project Context: Kindle Weather & PVE Dashboard

本项目是专为旧版 Kindle 实验性浏览器（E-ink 墨水屏）设计的零依赖家庭中控面板，部署在飞牛 OS NAS 虚拟机上，实时聚合天气、硬件状态、系统性能等信息。

## Core Goals
* **Reliability**: 兼容旧版 Kindle NetFront/WebKit 浏览器，无空白页。
* **Minimalist Aesthetic**: 高对比度黑白 Table 栅格对齐，E-ink 屏幕极致清晰。
* **Low Maintenance**: 免 Key 免配额天气（Open-Meteo），systemd 自动托管。
* **Real-Time Hardware Awareness**: PVE 宿主 CPU/盘温、USB 移动硬盘温度、飞牛 OS 性能指标秒级更新。

## Architecture & Data Flow
```text
[Kindle Browser]
       │ (GET / 每 5 分钟全页刷新)
       │ (XHR /api/status 每 1 秒 AJAX 无闪刷新)
       ▼
[飞牛 OS 192.168.31.161:8088 - panel.py HTTP Server]
       │                         │                         │
       ▼                         ▼                         ▼
[天气线程 30min]        [局域网状态线程 1s]          [硬件温度线程 1s]
    Open-Meteo         PVE REST API (8006)         PVE /metrics:9101
    Open-Meteo AQI     /proc files (local)         sudo smartctl /dev/sdb
                       Redmi Router API (5s)
                            │
                       [PVE 192.168.31.200:9101]
                       pve-metrics.service
                       sensors -j + smartctl /dev/sda
```

## Key Components
* `panel.py`: 飞牛 OS 后端 HTTP 服务器 + 多线程状态采集（天气/PVE/路由器/硬件温度）。
* `pve-metrics.service` (on PVE): `/opt/pve-metrics/exporter.py` Python stdlib metrics 导出器。
* `kindle-panel.service`: 飞牛 OS systemd 自启动、崩溃自愈服务。
* `ssh_run.py` & `scp_put.py`: 基于 pexpect 的 SSH/SCP 交互自动化工具。
* `run.sh`: IDE 静默执行包装脚本，规避命令确认弹窗。

## Version History
* `v1.0.0` (2026-05-25): 天气日历基础面板
* `v1.1.0` (2026-05-25): FlyOS 运行状态 + 双栏布局 + AJAX 秒刷
* `v1.2.0` (2026-05-29): PVE 主机温度扩展 + USB 盘 SMART + 布局优化 + 1s 刷新
