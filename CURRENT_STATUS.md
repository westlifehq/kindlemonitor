# Current Status: Kindle Weather & PVE Dashboard v1.2

## Completed Milestones

### v1.0–v1.1 基础
* **Zero-Auth Integration**: Open-Meteo 天气 + 空气质量接入（合肥包河 31.86, 117.28）。
* **Socket Monkeypatch**: 4 行 IPv4 强制解析补丁，解决飞牛 IPv6 DNS 超时故障。
* **PVE REST API 集成**: PVE 8006 端口 ticket 鉴权，实时采集 pve/101-fnos/102-istoreos 的磁盘/内存/CPU/在线时长。
* **FlyOS ProcFS 性能采集**: `/proc` 直读 uptime/CPU/内存/网络/IO，1s 高频刷新，零外部命令依赖。
* **Redmi AX6S 路由器集成**: MAC SHA1 签名动态登录，每 5s 采集 2.4G/5G 在线设备数。
* **AJAX 无闪实时刷新**: `/api/status` JSON 接口 + 前端 XHR 每 2s 刷新 DOM，规避 E-ink 全屏黑闪。
* **双栏 Table 布局**: 49% 天气 : 2% 间隔 : 49% 飞牛，Kindle 浏览器完美兼容，双侧 7 行高度对齐。
* **systemd 服务托管**: `kindle-panel.service` 开机自启、崩溃自愈。
* **凭证解耦 & Git 历史擦洗**: `.env` 隔离所有密钥，`git filter-branch` 彻底清除历史 commit 中的明文密码。

### v1.2 新增（本次会话）
* **PVE 主机温度 exporter**:
  - 在 PVE (192.168.31.200) 部署了 `pve-metrics.service`（`/opt/pve-metrics/exporter.py`），9101 端口，Python stdlib 实现。
  - 输出 CPU Package/核心温度（J4125，4 核）+ 宿主系统盘 `/dev/sda` SMART 温度（`smartmontools`）。
  - 安全 Token 鉴权（`X-Auth-Token`）+ iptables 放行 9101。
* **飞牛 USB 硬盘 SMART 采集**:
  - 识别飞牛 VM 内的 1TB USB 移动硬盘为 `/dev/sdb`。
  - 配置 `/etc/sudoers.d/kindle-panel-smartctl` 免密规则（`rvc ALL=(root) NOPASSWD: /usr/sbin/smartctl`）。
  - `sudo -n smartctl -A -j -d sat /dev/sdb` 读取温度。
* **硬件温度 1s 高频刷新**:
  - 新增独立后台线程 `refresh_hw_loop()`，`HW_REFRESH_SECONDS=1`。
  - AJAX 定时器由 2000ms 降至 **1000ms**。
  - `/api/status` 新增返回 `hw_rows`（`with lock` 外安全渲染，无死锁）。
* **主机状态卡片布局优化**:
  - 将"主机状态"卡片移至右列"飞牛 OS 运行状态"下方，左列完整呈现"未来 7 天"。
  - 双时间戳页脚：`天气 HH:MM · 主机 HH:MM`。
* **GitHub 同步**: 代码推送至 `westlifehq/kindlemonitor`，CHANGELOG.md 更新至 v1.2.0。

## Active Blockades
* 无。当前系统完全稳定运行。

## Live Endpoints
* 面板入口: `http://192.168.31.161:8088/`
* AJAX 状态接口: `http://192.168.31.161:8088/api/status`
* PVE 温度接口: `http://192.168.31.200:9101/metrics` (需 X-Auth-Token)
