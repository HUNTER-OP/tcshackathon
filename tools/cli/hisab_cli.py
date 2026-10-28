"""Hisab Kitab command-line chat client (backup demo + the brief's "command-line interface").
Usage: python hisab_cli.py --base-url http://10.127.10.203:8000 --customer CUST001 --mode hybrid
Commands: /customer CUST003   /mode local|hybrid   /clear   /quit      (needs: pip install httpx rich)
"""
from __future__ import annotations

import argparse
import json
import sys

import httpx
from rich.console import Console
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")

console = Console()


def inr(x) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x)
    neg, v = v < 0, abs(v)
    whole, frac = divmod(round(v * 100), 100)
    s = str(int(whole))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    out = f"₹{s}" + (f".{int(frac):02d}" if frac else "")
    return f"-{out}" if neg else out


def kv_table(title: str, rows: list[tuple[str, str]]) -> Table:
    t = Table(title=title, show_header=False, title_style="bold cyan", box=None, padding=(0, 2))
    t.add_column(style="dim")
    t.add_column(style="bold")
    for k, v in rows:
        t.add_row(k, v)
    return t


def render_card(card: dict) -> None:
    kind, d = card.get("type"), card.get("data") or {}
    if kind == "balance":
        console.print(kv_table("Balance", [
            ("Account", f"{d.get('account', '')} ({d.get('account_type', '')})"),
            ("Balance", inr(d.get("balance"))),
            ("As of", str(d.get("as_of", ""))),
        ]))
    elif kind == "transactions":
        t = Table(title="Transactions", title_style="bold cyan")
        for col in ("Date", "Description", "Category", "Amount", "Balance"):
            t.add_column(col, justify="right" if col in ("Amount", "Balance") else "left")
        for it in d.get("items", []):
            amt = it.get("amount", 0)
            t.add_row(str(it.get("date", ""))[:10], it.get("description", ""), it.get("category", ""),
                      f"[{'red' if amt < 0 else 'green'}]{inr(amt)}[/]", inr(it.get("balance_after")))
        console.print(t)
    elif kind == "spending":
        t = Table(title=f"Spending, last {d.get('days', '?')} days", title_style="bold cyan")
        t.add_column("Category")
        t.add_column("Amount", justify="right")
        for cat, amt in (d.get("by_category") or {}).items():
            style = "bold yellow" if cat == d.get("asked_category") else ""
            t.add_row(f"[{style}]{cat}[/]" if style else cat, inr(amt))
        t.add_row("[bold]Total debit[/]", f"[bold]{inr(d.get('total_debit'))}[/]")
        t.add_row("Total credit", inr(d.get("total_credit")))
        console.print(t)
    elif kind == "loan":
        ok = d.get("eligible")
        rows = [
            ("Product", str(d.get("product", d.get("loan_type", "")))),
            ("Eligible", "[green]Yes[/]" if ok else "[red]No[/]"),
            ("Requested", inr(d.get("requested_amount"))),
            ("Max amount", inr(d.get("max_amount"))),
            ("Tenure", f"{d.get('tenure_months', '?')} months"),
            ("Rate", f"{d.get('rate', '?')}%"),
            ("EMI", inr(d.get("emi"))),
            ("Existing EMI", inr(d.get("existing_emi", 0))),
            ("Processing fee", inr(d.get("processing_fee"))),
        ]
        if d.get("foir_after") is not None:
            rows.append(("FOIR after", f"{float(d['foir_after']) * 100:.1f}%"))
        for r in d.get("reasons") or []:
            rows.append(("Reason", str(r)))
        console.print(kv_table("Loan", rows))
    elif kind == "rates":
        dep = d.get("deposits") or {}
        if dep.get("fd"):
            t = Table(title="FD rates", title_style="bold cyan")
            t.add_column("Tenor")
            t.add_column("Rate", justify="right")
            for f in dep["fd"]:
                t.add_row(f["tenor"], f"{f['rate']}%")
            if dep.get("savings"):
                t.add_row("Savings", f"{dep['savings']['rate']}%")
            if dep.get("rd"):
                t.add_row("RD", f"{dep['rd']['rate']}%")
            console.print(t)
        if d.get("loans"):
            t = Table(title="Loan rates", title_style="bold cyan")
            for col in ("Loan", "Rate", "Max tenure", "Max amount"):
                t.add_column(col, justify="left" if col == "Loan" else "right")
            for l in d["loans"].values():
                t.add_row(l["name"], f"{l['rate']}%", f"{l['max_tenure_months']} mo", inr(l["max_amount"]))
            console.print(t)
    elif kind == "offer":
        console.print(Panel(f"{d.get('description', '')}\n[dim]{d.get('reason', '')}[/]",
                            title=f"[bold magenta]Offer: {d.get('title', '')}[/]",
                            subtitle=escape(f"[{d.get('cta', '')}]"), border_style="magenta"))
    elif kind in ("consent", "followup", "faq") and isinstance(d, dict) and len(d) <= 3:
        console.print(Panel("\n".join(str(v) for v in d.values()), title=f"[cyan]{kind}[/]", border_style="cyan"))
    elif kind == "handoff":
        console.print(Panel(json.dumps(d, ensure_ascii=False, indent=1), title="[bold red]Handoff ticket[/]",
                            border_style="red"))
    else:
        console.print(Panel(json.dumps(d, ensure_ascii=False, indent=1)[:800], title=f"[cyan]{kind}[/]",
                            border_style="cyan"))


def trace_line(r: dict) -> str:
    ents = r.get("entities") or {}
    ent_s = ", ".join(f"{k}={v}" for k, v in ents.items()) or "-"
    tools = ", ".join(tc.get("tool", "?") for tc in r.get("tool_calls") or []) or "-"
    conf = r.get("confidence")
    conf_s = f"{conf * 100:.0f}%" if isinstance(conf, (int, float)) else "?"
    return (f"{r.get('language', '?')} · {r.get('intent', '?')} ({conf_s}) · {ent_s} · tools: {tools} · "
            f"redactions: {r.get('redactions', 0)} · {r.get('model_used', '?')} · {r.get('latency_ms', '?')} ms")


def main() -> None:
    ap = argparse.ArgumentParser(description="Hisab Kitab CLI")
    ap.add_argument("--base-url", default="http://10.127.10.203:8000")
    ap.add_argument("--customer", default="CUST001")
    ap.add_argument("--mode", default="hybrid", choices=["hybrid", "local"])
    args = ap.parse_args()

    base, customer, mode = args.base_url.rstrip("/"), args.customer.upper(), args.mode
    history: list[dict] = []
    client = httpx.Client(timeout=60)

    names = {}
    try:
        names = {c["id"]: c["name"] for c in client.get(f"{base}/customers").json()}
    except Exception as e:  # backend down is shown on first message too
        console.print(f"[yellow]Could not load /customers: {e}[/]")

    console.print(Panel(f"Hisab Kitab CLI · {base}\nCommands: /customer ID · /mode local|hybrid · /clear · /quit",
                        border_style="green"))

    while True:
        try:
            msg = console.input(f"[bold green]{customer} {escape(names.get(customer, ''))} \\[{mode}] >[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not msg:
            continue
        if msg.startswith("/"):
            cmd, _, arg = msg.partition(" ")
            if cmd in ("/quit", "/exit", "/q"):
                break
            if cmd == "/customer" and arg:
                customer, history = arg.strip().upper(), []
                console.print(f"[dim]Switched to {customer} {names.get(customer, '')}; history cleared[/]")
            elif cmd == "/mode" and arg.strip() in ("local", "hybrid"):
                mode = arg.strip()
                console.print(f"[dim]Mode: {mode}[/]")
            elif cmd == "/clear":
                history = []
                console.print("[dim]History cleared[/]")
            else:
                console.print("[yellow]Unknown command[/]")
            continue

        try:
            with console.status("thinking..."):
                resp = client.post(f"{base}/chat", json={"message": msg, "customer_id": customer,
                                                          "mode": mode, "history": history})
                resp.raise_for_status()
                r = resp.json()
        except Exception as e:
            console.print(f"[red]Request failed: {e}[/]")
            continue

        console.print(Panel(Markdown(r.get("reply", "")), title="Hisab Kitab", border_style="blue"))
        for card in r.get("cards") or []:
            render_card(card)
        console.print(f"[dim]{trace_line(r)}[/]")
        if r.get("suggestions"):
            console.print("[dim]Try: " + " | ".join(r["suggestions"]) + "[/]")
        history += [{"role": "user", "content": msg}, {"role": "assistant", "content": r.get("reply", "")}]
        history = history[-12:]


if __name__ == "__main__":
    main()
