# Workspace Rules: Kindle Weather & Calendar Dashboard

## 1. Remote SSH Execution
* Always use `ssh_run.py` to run remote shell commands. Do not write raw sshpass wrappers.
* Ensure `stty -echo` is executed right after connection to suppress echoed commands in standard output.
* If executing via Agent, wrap commands inside [run.sh](file:///Users/hq/Desktop/AI/ANTIGRAVITY/kindle/run.sh) for silent execution.

## 2. Deploy Paths
* Project Root on Host: `/vol1/@appdata/kindle-panel` (Must keep owned by `rvc:Users` to avoid permission issues).
* Systemd Service: `/etc/systemd/system/kindle-panel.service`.
* Environment file: `/vol1/@appdata/kindle-panel/.env` (Permission must be kept at `600`).

## 3. Kindle Compatibility Guardrails
* **No Flexbox**: Use `<table>` grids for alignment.
* **No Tailwind CDN**: Use raw internal CSS styles.
* **Disable Anti-Aliasing**: Must include `-webkit-font-smoothing: none;` in `<body>`.
* **Meta Refresh**: Set auto-refresh in HTML using `<meta http-equiv="refresh" content="300">`.
