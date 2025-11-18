"""Update command implementation - updates times-tables CLI to latest version."""

import subprocess
import sys

from rich.console import Console

console = Console()


def update_cli(version: str | None = None) -> int:
    """Update times-tables CLI to latest version from GitHub.

    Args:
        version: Specific version tag to install (e.g., 'v0.2.0'). If None, installs latest.

    Returns:
        0 on success, 1 on error
    """
    repo_url = "git+https://github.com/dlg0/times-tables"

    if version:
        install_url = f"{repo_url}@{version}"
        console.print(f"[cyan]Updating times-tables to {version}...[/cyan]")
    else:
        install_url = repo_url
        console.print("[cyan]Updating times-tables to latest version...[/cyan]")

    # Try uv first, fallback to pip
    try:
        # Check if uv is available
        result = subprocess.run(
            ["uv", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            # Use uv tool install
            cmd = ["uv", "tool", "install", "--force", install_url]
            console.print("[dim]Using uv...[/dim]")
        else:
            # Fallback to pip
            cmd = [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--upgrade",
                "--force-reinstall",
                install_url,
            ]
            console.print("[dim]Using pip...[/dim]")

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            console.print("[green]✓[/green] Successfully updated times-tables")

            # Get the installed version
            try:
                version_result = subprocess.run(
                    ["times-tables", "--version"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if version_result.returncode == 0:
                    # Extract version from output like "times-tables 0.2.2"
                    installed_version = version_result.stdout.strip().split()[-1]
                    console.print(f"[dim]Installed version: {installed_version}[/dim]")
            except Exception:
                pass  # Don't fail if we can't get version

            return 0
        else:
            console.print("[red]Error:[/red] Update failed")
            console.print(result.stderr)
            return 1

    except FileNotFoundError:
        console.print("[red]Error:[/red] Neither uv nor pip found")
        console.print("Please install uv or ensure pip is available")
        return 1
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        return 1
