#!/usr/bin/env python3
"""Synthetic "Acme Orders" app for a browser-tool head-to-head.

Usage: python3 -u server.py <port>   (one request per log line on stdout)
       python3 server.py --answer    (prints the expected answer to task 1 of brief.md)
"""
import json
import random
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 18792
TOKEN = "tok-7f3a91"

rng = random.Random(42)
CUSTOMERS = ["Acme", "Globex", "Initech", "Umbrella", "Hooli", "Stark", "Wayne", "Wonka"]
STATUSES = ["pending", "shipped", "cancelled", "refunded"]
ORDERS = [
    {
        "id": f"ORD-{1000 + i}",
        "customer": rng.choice(CUSTOMERS),
        "status": rng.choices(STATUSES, weights=[3, 5, 1, 1])[0],
        "total": round(rng.uniform(20, 2000), 2),
        "date": f"2026-0{rng.randint(6, 9)}-{rng.randint(10, 28)}",
    }
    for i in range(240)
]
SETTINGS = {"display_name": "Demo User", "email": "demo@example.com"}

LOGIN_HTML = """<!doctype html><html><head><title>Acme Orders - Sign in</title>
<style>body{font-family:sans-serif;max-width:360px;margin:60px auto} label{display:block;margin-top:12px} .err{color:#b00}</style></head>
<body><h1>Acme Orders</h1>
<form id="login"><label>Username <input name="username" autocomplete="username"></label>
<label>Password <input name="password" type="password" autocomplete="current-password"></label>
<button type="submit" style="margin-top:16px">Sign in</button><p class="err" id="err" role="alert"></p></form>
<script>
document.getElementById('login').addEventListener('submit', async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  const res = await fetch('/api/login', {method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({username: f.get('username'), password: f.get('password')})});
  if (!res.ok) { document.getElementById('err').textContent = 'Invalid username or password'; return; }
  const data = await res.json();
  localStorage.setItem('token', data.token);
  location.href = '/app#orders';
});
</script></body></html>"""

APP_HTML = """<!doctype html><html><head><title>Acme Orders</title>
<style>body{font-family:sans-serif;margin:0} nav{background:#223;padding:10px} nav a{color:#fff;margin-right:16px}
main{padding:16px} table{border-collapse:collapse} td,th{border:1px solid #ccc;padding:3px 8px}
#toast{position:fixed;bottom:16px;right:16px;background:#2a2;color:#fff;padding:8px 12px;display:none}</style></head>
<body><nav><a href="#orders">Orders</a><a href="#settings">Settings</a><a href="#" id="logout">Log out</a></nav>
<main id="main">Loading...</main><div id="toast" role="status"></div>
<script src="/static/app.js"></script></body></html>"""

APP_JS = r"""
const token = localStorage.getItem('token');
if (!token) location.href = '/';
const api = (path, opts = {}) => fetch(path, {...opts, headers: {...(opts.headers || {}), 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}});
const main = document.getElementById('main');
function toast(msg) { const t = document.getElementById('toast'); t.textContent = msg; t.style.display = 'block'; setTimeout(() => t.style.display = 'none', 3000); }
document.getElementById('logout').onclick = () => { localStorage.removeItem('token'); location.href = '/'; };

async function renderOrders() {
  main.innerHTML = '<h1>Orders</h1><p>Loading orders...</p>';
  const orders = await (await api('/api/orders')).json();
  main.innerHTML = `<h1>Orders</h1>
    <label>Status <select id="status"><option value="">All</option><option>pending</option><option>shipped</option><option>cancelled</option><option>refunded</option></select></label>
    <label>Customer <input id="q" placeholder="Search customer"></label>
    <p id="count"></p>
    <table><thead><tr><th>Order</th><th>Customer</th><th>Status</th><th>Total</th><th>Date</th></tr></thead><tbody id="rows"></tbody></table>`;
  const draw = () => {
    const s = document.getElementById('status').value, q = document.getElementById('q').value.toLowerCase();
    const shown = orders.filter(o => (!s || o.status === s) && (!q || o.customer.toLowerCase().includes(q)));
    document.getElementById('count').textContent = `Showing ${shown.length} of ${orders.length} orders`;
    document.getElementById('rows').innerHTML = shown.map(o => `<tr><td>${o.id}</td><td>${o.customer}</td><td>${o.status}</td><td>$${o.total.toFixed(2)}</td><td>${o.date}</td></tr>`).join('');
  };
  document.getElementById('status').onchange = draw;
  document.getElementById('q').oninput = draw;
  draw();
}

async function renderSettings() {
  const s = await (await api('/api/settings')).json();
  main.innerHTML = `<h1>Settings</h1><form id="settings">
    <p><label>Display name <input name="displayName" value="${s.display_name}"></label></p>
    <p><label>Email <input name="email" value="${s.email}"></label></p>
    <button type="submit">Save</button></form>`;
  document.getElementById('settings').addEventListener('submit', async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    const res = await api('/api/settings', {method: 'POST', body: JSON.stringify({displayName: f.get('displayName'), email: f.get('email')})});
    const data = await res.json();
    toast('Saved changes for ' + data.user.name);
  });
}

const route = () => (location.hash === '#settings' ? renderSettings() : renderOrders());
window.addEventListener('hashchange', route);
route();
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send(self, code, body, ctype="application/json"):
        data = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        print(f"{time.strftime('%H:%M:%S')}\t{PORT}\t{self.command}\t{self.path}\t{code}", flush=True)

    def authed(self):
        return self.headers.get("Authorization") == f"Bearer {TOKEN}"

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            return {}

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            return self.send(200, LOGIN_HTML, "text/html")
        if path == "/app":
            return self.send(200, APP_HTML, "text/html")
        if path == "/static/app.js":
            return self.send(200, APP_JS, "application/javascript")
        if path.startswith("/api/") and not self.authed():
            return self.send(401, {"error": "unauthorized"})
        if path == "/api/orders":
            time.sleep(0.4)
            return self.send(200, ORDERS)
        if path == "/api/settings":
            return self.send(200, SETTINGS)
        return self.send(404, {"error": "not found"})

    def do_POST(self):
        path = self.path.split("?")[0]
        data = self.body()
        if path == "/api/login":
            if data.get("username") == "demo" and data.get("password") == "demo123":
                return self.send(200, {"token": TOKEN})
            return self.send(401, {"error": "invalid credentials"})
        if not self.authed():
            return self.send(401, {"error": "unauthorized"})
        if path == "/api/settings":
            if not data.get("display_name"):
                return self.send(422, {"error": "display_name is required", "received_fields": sorted(data)})
            SETTINGS.update({k: data[k] for k in ("display_name", "email") if k in data})
            return self.send(200, {"ok": True, "user": {"name": SETTINGS["display_name"]}})
        return self.send(404, {"error": "not found"})


if __name__ == "__main__":
    if "--answer" in sys.argv:
        g = [o for o in ORDERS if o["customer"] == "Globex" and o["status"] == "pending"]
        print(len(g), round(sum(o["total"] for o in g), 2), [o["id"] for o in g])
        sys.exit()
    print(f"listening on 127.0.0.1:{PORT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
