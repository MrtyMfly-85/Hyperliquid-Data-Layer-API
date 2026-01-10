"""
Moon Dev's Depositor Dashboard
===============================
Beautiful terminal dashboard for tracking ALL Hyperliquid depositors

Built with love by Moon Dev
https://moondev.com

This script displays:
- Total unique depositors on Hyperliquid
- Recent depositors with amounts
- Deposit statistics and trends

This is the canonical list of everyone who has ever bridged USDC to Hyperliquid.

Usage: python 16_depositors.py
"""

import sys
import os
from datetime import datetime

# Add parent directory to path for API import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api import MoonDevAPI

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.align import Align
from rich import box

# Initialize Rich console
console = Console()


def create_banner():
    """Create the Moon Dev depositor banner"""
    banner = """██████╗ ███████╗██████╗  ██████╗ ███████╗██╗████████╗ ██████╗ ██████╗ ███████╗
██╔══██╗██╔════╝██╔══██╗██╔═══██╗██╔════╝██║╚══██╔══╝██╔═══██╗██╔══██╗██╔════╝
██║  ██║█████╗  ██████╔╝██║   ██║███████╗██║   ██║   ██║   ██║██████╔╝███████╗
██║  ██║██╔══╝  ██╔═══╝ ██║   ██║╚════██║██║   ██║   ██║   ██║██╔══██╗╚════██║
██████╔╝███████╗██║     ╚██████╔╝███████║██║   ██║   ╚██████╔╝██║  ██║███████║
╚═════╝ ╚══════╝╚═╝      ╚═════╝ ╚══════╝╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚══════╝"""
    return Panel(
        Align.center(Text(banner, style="bold cyan")),
        title="🏦 [bold magenta]HYPERLIQUID DEPOSITOR TRACKER[/bold magenta] 🏦",
        subtitle="[dim]Every address that ever bridged to Hyperliquid | by Moon Dev[/dim]",
        border_style="bright_cyan",
        box=box.DOUBLE_EDGE,
        padding=(0, 1)
    )


def format_usd(value):
    """Format USD value with commas and dollar sign"""
    if value is None or value == 0:
        return "$0"
    if abs(value) >= 1_000_000_000:
        return f"${value/1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"${value/1_000_000:.2f}M"
    elif abs(value) >= 1_000:
        return f"${value/1_000:.1f}K"
    return f"${value:,.0f}"


def format_count(value):
    """Format count with K/M suffixes"""
    if value is None or value == 0:
        return "0"
    if value >= 1_000_000:
        return f"{value/1_000_000:.1f}M"
    elif value >= 1_000:
        return f"{value/1_000:.1f}K"
    return f"{value:,}"


def display_depositor_stats(depositors_data):
    """Display depositor statistics"""
    console.print(Panel(
        "📊 [bold white]DEPOSITOR STATISTICS[/bold white]  [dim cyan]GET https://api.moondev.com/api/depositors.json[/dim cyan]",
        border_style="bright_white",
        padding=(0, 1)
    ))

    if isinstance(depositors_data, dict):
        depositors = depositors_data.get('depositors', depositors_data.get('addresses', []))
        stats = depositors_data.get('stats', {})
    elif isinstance(depositors_data, list):
        depositors = depositors_data
        stats = {}
    else:
        depositors = []
        stats = {}

    total_depositors = len(depositors) if depositors else stats.get('total_count', 0)
    total_volume = stats.get('total_volume', stats.get('total_deposited', 0))

    # Main stats panel
    main_panel = Panel(
        f"[bold white]🏦 TOTAL DEPOSITORS[/bold white]\n\n"
        f"[bold cyan]{format_count(total_depositors)}[/bold cyan] unique addresses\n"
        f"[dim]Every wallet that bridged to Hyperliquid[/dim]",
        border_style="cyan",
        width=40,
        padding=(1, 2)
    )

    # Volume panel
    if total_volume:
        volume_panel = Panel(
            f"[bold white]💰 TOTAL DEPOSITED[/bold white]\n\n"
            f"[bold yellow]{format_usd(total_volume)}[/bold yellow] USDC\n"
            f"[dim]Lifetime bridge volume[/dim]",
            border_style="yellow",
            width=40,
            padding=(1, 2)
        )
        console.print(Columns([main_panel, volume_panel], equal=True, expand=True))
    else:
        console.print(main_panel)

    return depositors, stats


def display_recent_depositors(depositors_data):
    """Display recent depositors table"""
    console.print(Panel(
        "🆕 [bold green]RECENT DEPOSITORS[/bold green]  [dim cyan]GET https://api.moondev.com/api/depositors.json[/dim cyan]",
        border_style="green",
        padding=(0, 1)
    ))

    if isinstance(depositors_data, dict):
        depositors = depositors_data.get('depositors', depositors_data.get('addresses', []))
        # Try to get recent depositors specifically
        recent = depositors_data.get('recent', depositors[:25] if depositors else [])
    elif isinstance(depositors_data, list):
        recent = depositors_data[:25]
    else:
        recent = []

    table = Table(
        box=box.ROUNDED,
        border_style="green",
        header_style="bold magenta",
        padding=(0, 1),
        expand=True
    )

    table.add_column("#", style="dim", width=4)
    table.add_column("Depositor Address", style="cyan", width=44)
    table.add_column("Amount", style="yellow", justify="right", width=14)
    table.add_column("Time", style="dim", width=12)

    if not recent:
        table.add_row("", "[dim]No recent depositors found[/dim]", "", "")
    else:
        for i, depositor in enumerate(recent[:25], 1):
            if isinstance(depositor, dict):
                address = depositor.get('address', depositor.get('wallet', 'N/A'))
                amount = depositor.get('amount', depositor.get('value', 0))
                timestamp = depositor.get('timestamp', depositor.get('time', ''))

                if isinstance(amount, (int, float)) and amount > 0:
                    amount_str = format_usd(amount)
                else:
                    amount_str = "[dim]--[/dim]"

                if timestamp:
                    if isinstance(timestamp, (int, float)):
                        if timestamp > 1e10:
                            timestamp = timestamp / 1000
                        try:
                            time_str = datetime.fromtimestamp(timestamp).strftime("%m-%d %H:%M")
                        except:
                            time_str = str(timestamp)[:10]
                    else:
                        time_str = str(timestamp)[:10]
                else:
                    time_str = "[dim]--[/dim]"
            else:
                # Just an address string
                address = str(depositor)
                amount_str = "[dim]--[/dim]"
                time_str = "[dim]--[/dim]"

            # Rank emoji for top 3
            rank = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else str(i)

            table.add_row(rank, address, amount_str, time_str)

    console.print(table)


def display_depositor_sample(depositors):
    """Display sample of all depositor addresses"""
    console.print(Panel(
        "📋 [bold cyan]DEPOSITOR ADDRESS SAMPLE[/bold cyan]  [dim cyan]GET https://api.moondev.com/api/depositors.json[/dim cyan]",
        border_style="cyan",
        padding=(0, 1)
    ))

    if not depositors:
        console.print("[dim]No depositors found[/dim]")
        return

    table = Table(
        box=box.SIMPLE,
        border_style="cyan",
        header_style="bold white",
        padding=(0, 1)
    )

    table.add_column("#", style="dim", width=6)
    table.add_column("Address", style="cyan", width=44)
    table.add_column("Status", style="green", width=10)

    # Show first 20 depositors
    sample = depositors[:20]
    for i, depositor in enumerate(sample, 1):
        if isinstance(depositor, dict):
            address = depositor.get('address', depositor.get('wallet', str(depositor)))
        else:
            address = str(depositor)

        table.add_row(str(i), address, "🏦 Active")

    if len(depositors) > 20:
        table.add_row("...", f"[dim]+ {len(depositors) - 20:,} more addresses[/dim]", "")

    console.print(table)


def create_footer():
    """Create footer with timestamp and branding"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return Text(
        f"━━━ 🌙 Moon Dev's Depositor Tracker | {now} | api.moondev.com | The canonical Hyperliquid address list ━━━",
        style="dim cyan",
        justify="center"
    )


def main():
    """Main function - Moon Dev's Depositor Dashboard"""
    console.clear()
    console.print(create_banner())

    # Initialize API - Moon Dev
    console.print("[dim]🌙 Connecting to Moon Dev API...[/dim]")
    api = MoonDevAPI()

    if not api.api_key:
        console.print(Panel(
            "[bold red]ERROR:[/bold red] No API key found!\n"
            "Set MOONDEV_API_KEY in .env | Get key at: [cyan]moondev.com[/cyan]",
            title="[red]Auth Error[/red]",
            border_style="red",
            padding=(0, 1)
        ))
        return

    console.print("[dim green]✅ API connected[/dim green]")
    console.print()

    # Fetch depositors data - Moon Dev
    console.print("[bold cyan]🏦 Fetching all Hyperliquid depositors...[/bold cyan]")

    try:
        depositors_data = api.get_depositors()
    except AttributeError:
        # If get_depositors doesn't exist yet, try direct API call
        import requests
        headers = {'X-API-Key': api.api_key}
        response = requests.get(f"{api.base_url}/api/depositors.json", headers=headers)
        depositors_data = response.json() if response.status_code == 200 else {}
    except Exception as e:
        console.print(f"[red]Error fetching depositors: {e}[/red]")
        depositors_data = {}

    console.print()

    # Display sections
    depositors, stats = display_depositor_stats(depositors_data)
    console.print()

    display_recent_depositors(depositors_data)
    console.print()

    display_depositor_sample(depositors)

    # Summary
    if isinstance(depositors_data, dict):
        total = len(depositors_data.get('depositors', depositors_data.get('addresses', [])))
    elif isinstance(depositors_data, list):
        total = len(depositors_data)
    else:
        total = 0

    summary = (
        f"🏦 [cyan]{format_count(total)}[/cyan] total depositors | "
        f"📋 Canonical address list | "
        f"🔗 Arbitrum bridge tracked | "
        f"🌙 [magenta]Moon Dev Data Layer[/magenta]"
    )
    console.print(Panel(summary, title="[bold cyan]Summary[/bold cyan]  [dim cyan]GET https://api.moondev.com/api/depositors.json[/dim cyan]", border_style="cyan", padding=(0, 1)))

    console.print()
    console.print(create_footer())


if __name__ == "__main__":
    main()
