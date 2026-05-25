#!/usr/bin/env python3
# Kindle 浏览器能力测试 · 零依赖
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime

HTML = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="15">
<title>Kindle 测试</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: serif, "PingFang SC", "Microsoft YaHei"; padding: 16px; font-size: 18px; color: #000; background: #fff; line-height: 1.4; }
h1 { font-size: 22px; border-bottom: 2px solid #000; padding-bottom: 6px; margin-bottom: 12px; }
h2 { font-size: 16px; background: #000; color: #fff; padding: 4px 8px; margin: 16px 0 8px; }
.box { border: 2px solid #000; padding: 10px; margin-bottom: 8px; }
.big { font-size: 48px; font-weight: bold; line-height: 1.0; }
.gray { background: #eee; }
.inv { background: #000; color: #fff; }
table { width: 100%; border-collapse: collapse; }
td { border: 1px solid #000; padding: 8px; vertical-align: top; }
.flex-row { display: flex; gap: 10px; }
.flex-row > div { flex: 1; border: 1px dashed #000; padding: 10px; }
.tick { font-size: 14px; color: #555; }
</style>
</head>
<body>
<h1>Kindle 浏览器能力测试 <span style="float:right;font-weight:400">__TIME__</span></h1>

<h2>① 中文 &amp; 字号</h2>
<div class="box">
  <p>你好，欢迎来到 Kindle 浏览器测试页面。</p>
  <p class="big">26.5℃</p>
  <p class="tick">↑ 上面这个数字应该非常大（约 48px）。</p>
</div>

<h2>② Table 布局（兼容性兜底）</h2>
<table>
  <tr><td><b>室内</b><br>26.5℃ / 58%</td><td><b>室外</b><br>26℃ 多云</td></tr>
  <tr><td><b>WAN</b><br>↓917 ↑90 Mbps</td><td><b>延迟</b><br>32 ms</td></tr>
</table>
<p class="tick">↑ 上面应该是 2×2 的方格。</p>

<h2>③ Flexbox 布局（老 Kindle 易失败）</h2>
<div class="flex-row">
  <div>左 · 室内</div>
  <div>中 · 室外</div>
  <div>右 · 网络</div>
</div>
<p class="tick">↑ 三个方块应该<b>横向</b>排列。如果竖向堆叠 = flexbox 不支持。</p>

<h2>④ 边框 &amp; 灰阶</h2>
<div class="box gray">浅灰背景（E-Ink 应显示为浅网点）</div>
<div class="box inv">反白：黑底白字</div>

<h2>⑤ 自动刷新（关键！）</h2>
<div class="box">
  <p>本页每 <b>15 秒</b>自动刷新一次。服务器渲染时间：</p>
  <p class="big">__TIME__</p>
  <p class="tick">↑ 看着不动就等 15 秒，应当自己跳。如果一直不动 = meta refresh 不生效。</p>
</div>

<h2>⑥ 总结对照</h2>
<table>
  <tr><td>① 中文 + 大字号</td><td>看 ① 是否渲染</td></tr>
  <tr><td>② Table</td><td>看是否成 2×2 网格</td></tr>
  <tr><td>③ Flexbox</td><td>横向 = OK，竖向 = 不行</td></tr>
  <tr><td>④ 灰阶 / 反白</td><td>看是否分得清</td></tr>
  <tr><td>⑤ Meta refresh</td><td>15 秒后时间是否变</td></tr>
</table>
</body>
</html>"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        now = datetime.now().strftime("%H:%M:%S")
        body = HTML.replace("__TIME__", now).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, fmt, *args):
        print(self.address_string(), self.command, self.path)

if __name__ == "__main__":
    print("Kindle 测试服务启动：http://<飞牛IP>:8088/")
    HTTPServer(("0.0.0.0", 8088), Handler).serve_forever()
