#!/usr/bin/env python3
"""
Show performance for Freqtrade containers whose *container name* contains 'COPY'.
- Uses docker ps to get container names + host port -> 8080
- If no host port is published, the container is listed with metrics as N/A
- Auth: username 'ft', password 'kamala'
- Now with beautiful color formatting!
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

# ANSI Color codes
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Text colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Background colors
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'


def colorize_profit(value: Optional[float]) -> str:
    """Color profit values: green for positive, red for negative, dim for zero/none"""
    if value is None:
        return f"{Colors.DIM}-{Colors.RESET}"
    
    pct_str = f"{value:.2f}%"
    if value > 0:
        return f"{Colors.BRIGHT_GREEN}{pct_str}{Colors.RESET}"
    elif value < 0:
        return f"{Colors.BRIGHT_RED}{pct_str}{Colors.RESET}"
    else:
        return f"{Colors.DIM}{pct_str}{Colors.RESET}"


def colorize_win_rate(value: Optional[float]) -> str:
    """Color win rate: green for >60%, yellow for 40-60%, red for <40%"""
    if value is None:
        return f"{Colors.DIM}-{Colors.RESET}"
    
    pct_str = f"{value:.2f}%"
    if value >= 60:
        return f"{Colors.BRIGHT_GREEN}{pct_str}{Colors.RESET}"
    elif value >= 40:
        return f"{Colors.YELLOW}{pct_str}{Colors.RESET}"
    else:
        return f"{Colors.BRIGHT_RED}{pct_str}{Colors.RESET}"


def colorize_profit_factor(pf_str: str) -> str:
    """Color profit factor: green for >1.5, yellow for 1.0-1.5, red for <1.0"""
    if pf_str == "-":
        return f"{Colors.DIM}-{Colors.RESET}"
    
    try:
        pf_val = float(pf_str)
        if pf_val >= 1.5:
            return f"{Colors.BRIGHT_GREEN}{pf_str}{Colors.RESET}"
        elif pf_val >= 1.0:
            return f"{Colors.YELLOW}{pf_str}{Colors.RESET}"
        else:
            return f"{Colors.BRIGHT_RED}{pf_str}{Colors.RESET}"
    except ValueError:
        return f"{Colors.DIM}{pf_str}{Colors.RESET}"


def colorize_trades(trades: Any) -> str:
    """Color trade count: bright for high activity, dim for low/none"""
    if trades == "-":
        return f"{Colors.DIM}-{Colors.RESET}"
    
    try:
        count = int(trades)
        if count >= 100:
            return f"{Colors.BRIGHT_CYAN}{count}{Colors.RESET}"
        elif count >= 50:
            return f"{Colors.CYAN}{count}{Colors.RESET}"
        elif count >= 10:
            return f"{Colors.WHITE}{count}{Colors.RESET}"
        else:
            return f"{Colors.DIM}{count}{Colors.RESET}"
    except (ValueError, TypeError):
        return f"{Colors.DIM}{trades}{Colors.RESET}"


def colorize_container_name(name: str) -> str:
    """Make container names stand out"""
    return f"{Colors.BOLD}{Colors.BRIGHT_BLUE}{name}{Colors.RESET}"


def colorize_port(port: Any) -> str:
    """Color port numbers"""
    if port == "-":
        return f"{Colors.DIM}-{Colors.RESET}"
    return f"{Colors.BRIGHT_MAGENTA}{port}{Colors.RESET}"


def colorize_strategy(strategy: str) -> str:
    """Color strategy names"""
    if strategy == "-":
        return f"{Colors.DIM}-{Colors.RESET}"
    return f"{Colors.BRIGHT_YELLOW}{strategy}{Colors.RESET}"


def colorize_bot_name(bot: str) -> str:
    """Color bot names"""
    if bot == "-":
        return f"{Colors.DIM}-{Colors.RESET}"
    return f"{Colors.CYAN}{bot}{Colors.RESET}"


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

    print(f"\n{Colors.BOLD}{Colors.BRIGHT_WHITE}🤖 Freqtrade Performance Monitor{Colors.RESET}")
    print(f"{Colors.DIM}Searching for containers with 'COPY' in the name...{Colors.RESET}\n")

    # 1) Get containers and filter by *container name* containing COPY
    conts = [c for c in docker_containers() if "copy" in c["name"].lower()]
    if not conts:
        print(f"{Colors.BRIGHT_RED}❌ No containers with 'COPY' in the name were found.{Colors.RESET}")
        return

    print(f"{Colors.GREEN}✅ Found {len(conts)} container(s) with 'COPY' in the name{Colors.RESET}\n")

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

    # 3) Pretty print with colors
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
        
        # Apply specific coloring based on the column
        if key == "container":
            return colorize_container_name(str(v))
        elif key == "port":
            return colorize_port(v)
        elif key == "bot":
            return colorize_bot_name(str(v))
        elif key == "strategy":
            return colorize_strategy(str(v))
        elif key == "trades":
            return colorize_trades(v)
        elif key == "win_rate":
            return colorize_win_rate(v)
        elif key in ("profit_all", "profit_closed"):
            return colorize_profit(v)
        elif key == "max_dd":
            return colorize_profit(v)  # Max drawdown uses same coloring as profit (red for negative)
        elif key == "pf":
            return colorize_profit_factor(str(v))
        
        return str(v)

    # Calculate plain text widths (without color codes)
    def plain_text_len(text: str) -> int:
        """Remove ANSI escape sequences to get actual text length"""
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return len(ansi_escape.sub('', text))

    # widths
    col_w = {}
    for title, key in headers:
        w = len(title)
        for r in rows:
            cell_content = cell(key, r)
            w = max(w, plain_text_len(cell_content))
        col_w[title] = w

    # Create colored header
    header_row = " | ".join(f"{Colors.BOLD}{Colors.WHITE}{t:<{col_w[t]}}{Colors.RESET}" for t, _ in headers)
    separator = "-+-".join("-" * col_w[t] for t, _ in headers)
    
    print(header_row)
    print(f"{Colors.DIM}{separator}{Colors.RESET}")

    # sort: containers with data first, by Profit All desc, then trades
    def sort_key(r: Dict[str, Any]):
        has_data = 0 if r["trades"] == "-" else 1
        pa = r.get("profit_all")
        return (has_data, pa if isinstance(pa, (int, float)) else float("-inf"), r.get("trades") or -1)

    rows.sort(key=sort_key, reverse=True)

    # Print colored rows
    for i, r in enumerate(rows):
        # Add subtle alternating row background for better readability
        row_cells = []
        for title, key in headers:
            cell_content = cell(key, r)
            padding = col_w[title] - plain_text_len(cell_content)
            padded_cell = cell_content + " " * padding
            row_cells.append(padded_cell)
        
        row_line = " | ".join(row_cells)
        print(row_line)

    print(f"\n{Colors.DIM}Legend: {Colors.GREEN}Positive{Colors.RESET} {Colors.DIM}|{Colors.RESET} {Colors.RED}Negative{Colors.RESET} {Colors.DIM}|{Colors.RESET} {Colors.YELLOW}Neutral{Colors.RESET} {Colors.DIM}|{Colors.RESET} {Colors.DIM}No Data{Colors.RESET}")
    print(f"{Colors.DIM}Profit Factor: {Colors.GREEN}>1.5 Excellent{Colors.RESET} {Colors.DIM}|{Colors.RESET} {Colors.YELLOW}1.0-1.5 Good{Colors.RESET} {Colors.DIM}|{Colors.RESET} {Colors.RED}<1.0 Poor{Colors.RESET}")
    print(f"{Colors.DIM}Win Rate: {Colors.GREEN}>60% High{Colors.RESET} {Colors.DIM}|{Colors.RESET} {Colors.YELLOW}40-60% Medium{Colors.RESET} {Colors.DIM}|{Colors.RESET} {Colors.RED}<40% Low{Colors.RESET}\n")


if __name__ == "__main__":
    main()
