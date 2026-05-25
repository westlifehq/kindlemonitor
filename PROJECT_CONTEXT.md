# Project Context: Kindle Weather & Calendar Dashboard

This project is a lightweight, zero-dependency weather and calendar dashboard designed specifically for old Kindle Experimental Browsers (e-ink screens).

## Core Goals
* **Reliability**: Bulletproof rendering on older Kindle browsers (NetFront/WebKit-based), avoiding generic web app blank pages.
* **Minimalist Aesthetic**: High-contrast, sharp e-ink layout (black & white grid alignment) to ensure perfect legibility.
* **Low Maintenance**: Keyless, quota-free data fetching (Open-Meteo) and fully automated service persistence (systemd).

## Architecture & Data Flow
```text
[Kindle Browser] 
       │ (GET / every 5 mins)
       ▼
[FlyOS Host: Python HTTP Server (Port 8088)]
       │ (Reads state memory)
       ▼
[Thread-Safe Cached State] ◄─── (Fetches every 30 mins) ─── [Background Fetcher Thread]
                                                                  │ (IPv4 Only Socket)
                                                                  ▼
                                                          [Open-Meteo APIs]
```

## Key Components
* `panel.py`: Unified Python backend providing HTTP server and background fetcher thread.
* `kindle-panel.service`: Auto-boot and crash self-healing supervisor configuration.
* `ssh_run.py` & `scp_put.py`: Password-interactive SSH/SCP automation utilities using Python `pexpect`.
* `run.sh`: Secure local execution wrapper for silent, prompt-free CLI operations.
