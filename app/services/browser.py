"""
Browser Service — Step 41 & Step 47 (Multi-Browser Support)
Connects to the user's live browser (Brave, Google Chrome, Microsoft Edge, or Custom Chromium)
via Chrome DevTools Protocol (CDP) on the configured debugging port (default 9222).
Detects login state on LinkedIn, Indeed, Naukri, Wellfound.
Provides automatic browser launching and OS-specific command generators.
"""
import asyncio
import logging
import os
import platform
import shutil
import subprocess
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("browser_service")

# Supported browser definitions and known paths
BROWSER_METADATA: Dict[str, Dict[str, Any]] = {
    "brave": {
        "name": "Brave Browser",
        "icon": "lion",
        "binaries": ["brave.exe", "brave", "brave-browser"],
        "paths": {
            "Windows": [
                os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
                os.path.expandvars(r"%PROGRAMFILES%\BraveSoftware\Brave-Browser\Application\brave.exe"),
                os.path.expandvars(r"%PROGRAMFILES(X86)%\BraveSoftware\Brave-Browser\Application\brave.exe"),
                r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
            ],
            "Darwin": [
                "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
                os.path.expanduser("~/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"),
            ],
            "Linux": [
                "/usr/bin/brave-browser",
                "/usr/bin/brave",
                "/snap/bin/brave",
                "/usr/local/bin/brave-browser",
            ],
        },
    },
    "chrome": {
        "name": "Google Chrome",
        "icon": "globe",
        "binaries": ["chrome.exe", "google-chrome", "google-chrome-stable", "chrome"],
        "paths": {
            "Windows": [
                os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            ],
            "Darwin": [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            ],
            "Linux": [
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/chromium-browser",
                "/snap/bin/chromium",
            ],
        },
    },
    "edge": {
        "name": "Microsoft Edge",
        "icon": "edge",
        "binaries": ["msedge.exe", "microsoft-edge", "msedge"],
        "paths": {
            "Windows": [
                os.path.expandvars(r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe"),
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            ],
            "Darwin": [
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                os.path.expanduser("~/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
            ],
            "Linux": [
                "/usr/bin/microsoft-edge",
                "/usr/bin/microsoft-edge-stable",
            ],
        },
    },
    "custom": {
        "name": "Custom Chromium",
        "icon": "settings",
        "binaries": [],
        "paths": {
            "Windows": [],
            "Darwin": [],
            "Linux": [],
        },
    },
}


class BrowserNotAvailableError(Exception):
    """Raised when the CDP debugging port is not reachable."""


# Portal login-check specs: (check_url, js_expression_that_returns_truthy_when_logged_in)
PORTAL_SPECS: Dict[str, Dict[str, str]] = {
    "linkedin": {
        "url": "https://www.linkedin.com/feed/",
        "js": "!!document.querySelector('.global-nav__me') || !!document.querySelector('[data-control-name=\"nav.settings\"]')",
    },
    "indeed": {
        "url": "https://www.indeed.com/",
        "js": (
            "!!document.querySelector('[data-testid=\"UserDropdownTrigger\"]') || "
            "!!document.querySelector('.gnav-LoggedInUser') || "
            "!!document.querySelector('#indeed-ia-header-logged-in')"
        ),
    },
    "naukri": {
        "url": "https://www.naukri.com/",
        "js": (
            "(!document.querySelector('#login_Layer') && "
            "!!document.querySelector('.nI-gNb-logged-user')) || "
            "!!document.querySelector('.nI-gNb-user-name')"
        ),
    },
    "wellfound": {
        "url": "https://wellfound.com/",
        "js": (
            "!!document.querySelector('[data-test=\"UserAvatar\"]') || "
            "!!document.querySelector('.styles_userImage__') || "
            "!!document.querySelector('.nav-profile-link')"
        ),
    },
}


def get_browser_executable_path(browser_type: str = "brave", custom_path: Optional[str] = None) -> Optional[str]:
    """
    Locates the executable path for the requested browser on the current operating system.
    Checks custom path first, then OS-specific default directories, then PATH.
    """
    if custom_path and os.path.exists(custom_path):
        return os.path.abspath(custom_path)

    browser_key = (browser_type or "brave").lower()
    meta = BROWSER_METADATA.get(browser_key, BROWSER_METADATA["brave"])

    system = platform.system()
    known_paths = meta["paths"].get(system, [])

    # 1. Check known file paths
    for path in known_paths:
        if path and os.path.exists(path) and os.path.isfile(path):
            return path

    # 2. Check system PATH via binary names
    for binary in meta.get("binaries", []):
        which_path = shutil.which(binary)
        if which_path and os.path.exists(which_path):
            return which_path

    return None


def get_launch_commands(browser_type: str = "brave", port: int = 9222, custom_path: Optional[str] = None) -> Dict[str, str]:
    """
    Generates exact copy-paste launch commands for PowerShell, CMD, macOS terminal, and Linux.
    """
    browser_key = (browser_type or "brave").lower()
    detected_path = get_browser_executable_path(browser_key, custom_path)
    meta = BROWSER_METADATA.get(browser_key, BROWSER_METADATA["brave"])
    display_name = meta["name"]

    target_exe = detected_path or (
        "brave" if browser_key == "brave" else
        "chrome" if browser_key == "chrome" else
        "msedge" if browser_key == "edge" else "chromium"
    )

    # Windows CMD / PowerShell
    if '"' not in target_exe and " " in target_exe:
        quoted_exe = f'"{target_exe}"'
    else:
        quoted_exe = target_exe

    ps_cmd = f'& {quoted_exe} --remote-debugging-port={port}'
    cmd_cmd = f'start "" {quoted_exe} --remote-debugging-port={port}'
    bash_cmd = f'{quoted_exe} --remote-debugging-port={port} &'

    return {
        "browser_name": display_name,
        "port": port,
        "detected_path": detected_path or "Not found automatically",
        "powershell": ps_cmd,
        "cmd": cmd_cmd,
        "bash": bash_cmd,
    }


def launch_browser_instance(browser_type: str = "brave", port: int = 9222, custom_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Launches the chosen browser with the remote debugging port active as a background process.
    """
    browser_key = (browser_type or "brave").lower()
    executable = get_browser_executable_path(browser_key, custom_path)
    meta = BROWSER_METADATA.get(browser_key, BROWSER_METADATA["brave"])
    display_name = meta["name"]

    if not executable:
        commands = get_launch_commands(browser_key, port, custom_path)
        return {
            "success": False,
            "message": f"Could not find {display_name} executable automatically. Please provide the custom path or run the command manually.",
            "launch_commands": commands,
        }

    try:
        args = [executable, f"--remote-debugging-port={port}"]

        # Launch detached process across platforms
        if platform.system() == "Windows":
            # DETACHED_PROCESS = 0x00000008, CREATE_NEW_PROCESS_GROUP = 0x00000200
            flags = 0x00000008 | 0x00000200
            proc = subprocess.Popen(args, creationflags=flags, close_fds=True)
        else:
            proc = subprocess.Popen(args, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        logger.info(f"Launched {display_name} (PID {proc.pid}) with --remote-debugging-port={port}")
        return {
            "success": True,
            "pid": proc.pid,
            "message": f"{display_name} launched successfully with port {port}.",
            "executable": executable,
            "port": port,
        }
    except Exception as e:
        logger.error(f"Failed to launch {display_name}: {e}")
        return {
            "success": False,
            "message": f"Error launching {display_name}: {str(e)}",
            "executable": executable,
        }


@asynccontextmanager
async def get_cdp_browser(port: int = 9222, browser_type: str = "brave"):
    """
    Async context manager that connects to an already-running browser instance
    (Brave, Chrome, Edge, etc.) over the remote debugging port (CDP).

    Raises BrowserNotAvailableError if the port is not open.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise BrowserNotAvailableError(
            "playwright is not installed. Run: pip install playwright && playwright install chromium"
        )

    browser_key = (browser_type or "brave").lower()
    meta = BROWSER_METADATA.get(browser_key, BROWSER_METADATA["brave"])
    display_name = meta["name"]
    cdp_url = f"http://localhost:{port}"

    # Quick TCP check first — avoids hanging on playwright connect timeout
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        result = sock.connect_ex(("localhost", port))
        if result != 0:
            cmd = f"{browser_key} --remote-debugging-port={port}"
            raise BrowserNotAvailableError(
                f"{display_name} remote debugging port {port} is not open. "
                f"Launch {display_name} with: {cmd}"
            )
    finally:
        sock.close()

    playwright_ctx = async_playwright()
    playwright = await playwright_ctx.__aenter__()
    try:
        browser = await playwright.chromium.connect_over_cdp(cdp_url)
        yield browser
    except Exception as e:
        raise BrowserNotAvailableError(f"Could not connect to {display_name} on {cdp_url}: {e}") from e
    finally:
        try:
            await playwright_ctx.__aexit__(None, None, None)
        except Exception:
            pass


async def check_portal_login(browser, portal: str) -> bool:
    """
    Opens a background page, navigates to the portal's auth-indicator URL,
    evaluates a JS expression to detect login state, then closes the page.
    """
    spec = PORTAL_SPECS.get(portal)
    if not spec:
        return False

    page = None
    try:
        page = await browser.new_page()
        await page.route("**/*.{png,jpg,jpeg,gif,svg,webp,woff,woff2,ttf}", lambda r: r.abort())
        await page.goto(spec["url"], wait_until="domcontentloaded", timeout=15000)
        result = await page.evaluate(spec["js"])
        return bool(result)
    except Exception as e:
        logger.debug(f"Portal login check failed for {portal}: {e}")
        return False
    finally:
        if page:
            try:
                await page.close()
            except Exception:
                pass


async def detect_all_portals(browser) -> Dict[str, bool]:
    """
    Run login checks for all supported portals concurrently.
    Returns {portal_name: is_logged_in}.
    """
    results: Dict[str, bool] = {}
    tasks = {portal: check_portal_login(browser, portal) for portal in PORTAL_SPECS}

    gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)
    for portal, result in zip(tasks.keys(), gathered):
        if isinstance(result, Exception):
            logger.debug(f"Portal {portal} check raised: {result}")
            results[portal] = False
        else:
            results[portal] = bool(result)

    return results


async def get_browser_status(port: int = 9222, browser_type: str = "brave", custom_path: Optional[str] = None) -> Dict[str, Any]:
    """
    High-level helper: checks CDP reachability and all portal login states.
    Includes supported browser list, detected executable path, and copyable commands.
    """
    browser_key = (browser_type or "brave").lower()
    meta = BROWSER_METADATA.get(browser_key, BROWSER_METADATA["brave"])
    display_name = meta["name"]
    launch_commands = get_launch_commands(browser_key, port, custom_path)
    detected_path = get_browser_executable_path(browser_key, custom_path)

    supported_browsers = [
        {"id": k, "name": v["name"], "icon": v["icon"], "detected": bool(get_browser_executable_path(k))}
        for k, v in BROWSER_METADATA.items()
    ]

    try:
        async with get_cdp_browser(port=port, browser_type=browser_key) as browser:
            portals = await detect_all_portals(browser)
            return {
                "cdp_reachable": True,
                "browser_type": browser_key,
                "browser_name": display_name,
                "port": port,
                "detected_path": detected_path,
                "supported_browsers": supported_browsers,
                "portals": portals,
                "launch_commands": launch_commands,
                "message": f"{display_name} CDP connected successfully on port {port}.",
            }
    except BrowserNotAvailableError as e:
        return {
            "cdp_reachable": False,
            "browser_type": browser_key,
            "browser_name": display_name,
            "port": port,
            "detected_path": detected_path,
            "supported_browsers": supported_browsers,
            "portals": {p: False for p in PORTAL_SPECS},
            "launch_commands": launch_commands,
            "message": str(e),
        }
    except Exception as e:
        return {
            "cdp_reachable": False,
            "browser_type": browser_key,
            "browser_name": display_name,
            "port": port,
            "detected_path": detected_path,
            "supported_browsers": supported_browsers,
            "portals": {p: False for p in PORTAL_SPECS},
            "launch_commands": launch_commands,
            "message": f"Unexpected error: {e}",
        }
