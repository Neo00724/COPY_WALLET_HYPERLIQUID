#!/usr/bin/env python3
"""
Show performance for Freqtrade containers whose *container name* contains 'COPY'.
- Uses docker ps to get container names + host port -> 8080
- If no host port is published, the container is listed with metrics as N/A
- Auth: username 'ft', password 'kamala'
"""

import re
import subprocess
from typing import Any, Dict, List, Optional

import requests
from requests.auth import HTTPBasicAuth

USERNAME = "ft"
PASSWORD = "kamala"
TIMEOUT = 3  # seconds

PORT_RE = re.compile(r"(?:\d{1,3}(?:\.\d{1,3}){3}:)?(\d+)->8080/tcp")


def docker_containers() -> List[Dict[str, Optional[int]]]:
    """
    Return [{'name': str, 'port': Optional[int]}] from docker ps.
    """
    try:
        out = subprocess.check_output(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Ports}}"], text=True
        )
    except Exception:
        return []

    rows: List[Dict[str, Optional[int]]] = []
    for line in out.splitlines():
        name, *port_parts = line.split("\t", 1)
        ports = port_parts[0] if port_parts else ""
        m = PORT_RE.search(ports or "")
        port = int(m.group(1)) if m else None
        rows.append({"name": name.strip(), "port": port})
    return rows


def get_json(url: str, auth: HTTPBasicAuth) -> Optional[Dict[str, Any]]:
    try:
        r = requests.get(url, auth=auth, timeout=TIMEOUT)
        if r.status_code == 200:
            return r.json()
    except requests.RequestException:
        pass
    return None


def pct(x: Optional[float]) -> str:
    return "-" if x is None else f"{x:.2f}%"


def main() -> None:
    auth = HTTPBasicAuth(USERNAME, PASSWORD)

    # 1) Get containers and filter by *container name* containing COPY
    conts = [c for c in docker_containers() if "copy" in c["name"].lower()]
    if not conts:
        print("No containers with 'COPY' in the name were found.")
        return

    # 2) Collect metrics (when port is available)
    rows: List[Dict[str, Any]] = []
    for c in conts:
        name, port = c["name"], c["port"]
        strategy = "-"
        bot_name = "-"

        if port is None:
            rows.append(
                {
                    "container": name,
                    "port": "-",
                    "bot": bot_name,
                    "strategy": strategy,
                    "trades": "-",
                    "win_rate": None,
                    "profit_all": None,
                    "profit_closed": None,
                    "pf": "-",
                    "max_dd": None,
                }
            )
            continue

        base = f"http://127.0.0.1:{port}/api/v1"
        cfg = get_json(f"{base}/show_config", auth) or {}
        bot_name = cfg.get("bot_name") or "-"
        strategy = cfg.get("strategy") or "-"

        prof = get_json(f"{base}/profit", auth)
        if not prof:
            rows.append(
                {
                    "container": name,
                    "port": port,
                    "bot": bot_name,
                    "strategy": strategy,
                    "trades": "-",
                    "win_rate": None,
                    "profit_all": None,
                    "profit_closed": None,
                    "pf": "-",
                    "max_dd": None,
                }
            )
            continue

        w = prof.get("winning_trades", 0) or 0
        l = prof.get("losing_trades", 0) or 0
        tc = prof.get("trade_count", 0) or 0
        closed = w + l
        win_rate = (w / closed * 100) if closed else None

        pf = prof.get("profit_factor")
        pf_str = "-" if pf is None else f"{pf:.2f}"

        mdd = prof.get("max_drawdown")
        mdd_pct = None if mdd is None else (mdd * 100 if abs(mdd) <= 1 else float(mdd))

        rows.append(
            {
                "container": name,
                "port": port,
                "bot": bot_name,
                "strategy": strategy,
                "trades": tc,
                "win_rate": win_rate,
                "profit_all": prof.get("profit_all_percent"),
                "profit_closed": prof.get("profit_closed_percent"),
                "pf": pf_str,
                "max_dd": mdd_pct,
            }
        )

    # 3) Pretty print
    headers = [
        ("CONTAINER", "container"),
        ("PORT", "port"),
        ("BOT", "bot"),
        ("STRATEGY", "strategy"),
        ("TRADES", "trades"),
        ("WIN RATE", "win_rate"),
        ("PROFIT ALL", "profit_all"),
        ("PROFIT CLOSED", "profit_closed"),
        ("PF", "pf"),
        ("MAX DD", "max_dd"),
    ]

    def cell(key: str, r: Dict[str, Any]) -> str:
        v = r.get(key)
        if key in ("win_rate", "profit_all", "profit_closed", "max_dd"):
            return pct(v)
        return str(v)

    # widths
    col_w = {}
    for title, key in headers:
        w = len(title)
        for r in rows:
            w = max(w, len(cell(key, r)))
        col_w[title] = w

    # header + sep
    print(" | ".join(f"{t:<{col_w[t]}}" for t, _ in headers))
    print("-+-".join("-" * col_w[t] for t, _ in headers))

    # sort: containers with data first, by Profit All desc, then trades
    def sort_key(r: Dict[str, Any]):
        has_data = 0 if r["trades"] == "-" else 1
        pa = r.get("profit_all")
        return (has_data, pa if isinstance(pa, (int, float)) else float("-inf"), r.get("trades") or -1)

    rows.sort(key=sort_key, reverse=True)

    for r in rows:
        print(" | ".join(f"{cell(key, r):<{col_w[title]}}" for title, key in headers))


if __name__ == "__main__":
    main()
