#!/usr/bin/env python3

# ╭──────────────────────────────────────╮
# │ setup.py on PyYPSH                   │
# │ Nercone <nercone@diamondgotcat.net>  │
# │ Made by Nercone / MIT License        │
# │ Copyright (c) 2025 DiamondGotCat     │
# ╰──────────────────────────────────────╯

from __future__ import annotations

import os
import sys
import platform
import tempfile
import shutil
import zipfile
import traceback
import argparse
from dataclasses import dataclass
from typing import Literal, Dict, Any, Callable, Optional, Tuple

import requests
from rich import print

# ─────────────────────────────────────────────────────────────────────────────
# Constants & Types
# ─────────────────────────────────────────────────────────────────────────────

Channel = Literal["stable", "maybe-stable", "beta", "custom"]
BuildType = Literal["pyinstaller", "nuitka"]

DEFAULT_DEST = os.path.join(os.path.expanduser("~"), ".ypsh", "bin")
BASE_CHANNEL_URL = "https://ypsh-dgc.github.io/YPSH/channels/"
GITHUB_RELEASE_BASE = "https://github.com/YPSH-DGC/YPSH/releases/download"


# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────

def passingGatekeeper(path: str) -> None:
    """Remove macOS quarantine flag (ignore errors silently)."""
    try:
        os.system(f"xattr -d com.apple.quarantine '{path}'")
    except Exception:
        pass


def getTagFromChannel(channel_id: str) -> str:
    """Resolve a release tag from a channel text file hosted on GitHub Pages."""
    r = requests.get(f"{BASE_CHANNEL_URL}{channel_id}.txt", timeout=10)
    r.raise_for_status()
    return r.text.strip()


def _normalize_platform() -> Tuple[str, str, str, bool]:
    """
    Returns (os_id, arch_id, friendly_platform, is_macos_gatekeeper_needed)
    os_id: 'macos' | 'linux' | 'windows'
    arch_id: 'amd64' | 'arm64'
    """
    system = platform.system()
    arch = platform.machine().lower()

    if arch in ("x86_64", "amd64"):
        arch_id = "amd64"
    elif arch in ("arm64", "aarch64"):
        arch_id = "arm64"
    else:
        raise RuntimeError(f"Unsupported CPU: {platform.machine()}")

    if system == "Darwin":
        os_id = "macos"
        friendly = "macOS Apple Silicon" if arch_id == "arm64" else "macOS Intel"
        gate = True
    elif system == "Linux":
        os_id = "linux"
        friendly = "Linux ARM" if arch_id == "arm64" else "Linux Intel/AMD"
        gate = False
    elif system == "Windows":
        os_id = "windows"
        friendly = "Windows ARM" if arch_id == "arm64" else "Windows Intel/AMD"
        gate = False
    else:
        raise RuntimeError(f"Unsupported OS: {system}")

    return os_id, arch_id, friendly, gate


def _artifact_names(
    os_id: str, arch_id: str, build: BuildType
) -> Tuple[str, str, str]:
    """
    Compute (zip_filename, inner_binary_name, recommended_filename)
    - Adds '-NUI' for Nuitka artifacts
    - Keeps existing naming scheme; only inserts suffix
    """
    suffix = "-NUI" if build == "nuitka" else ""
    base = f"YPSH-{os_id}-{arch_id}{suffix}"
    zip_filename = f"{base}.zip"
    inner_binary = base + (".exe" if os_id == "windows" else "")
    recommended_filename = "ypsh.exe" if os_id == "windows" else "ypsh"
    return zip_filename, inner_binary, recommended_filename


def getAutoBuildInformation(tag: str, *, build: BuildType) -> Dict[str, Any]:
    """
    Returns metadata needed for downloading & installing the correct artifact.
    """
    try:
        os_id, arch_id, friendly, gate = _normalize_platform()
    except RuntimeError as e:
        return {"status": "error", "desc": str(e)}

    zip_name, inner_binary, final_name = _artifact_names(os_id, arch_id, build)
    url = f"{GITHUB_RELEASE_BASE}/{tag}/{zip_name}"

    return {
        "status": "ok",
        "platform": friendly,
        "url": url,
        "origin_filename": inner_binary,
        "recommended_filename": final_name,
        "isGatekeeperCommandRequire": gate,
    }


# ─────────────────────────────────────────────────────────────────────────────
# PATH helpers
# ─────────────────────────────────────────────────────────────────────────────

def _add_to_path_posix(path_dir: str) -> list[str]:
    home = os.path.expanduser("~")
    shell = os.path.basename(os.environ.get("SHELL", "bash")).lower()

    def contains(p: str) -> bool:
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                return path_dir in fh.read()
        except Exception:
            return False

    known_files = [
        os.path.join(home, ".zprofile"),
        os.path.join(home, ".zshrc"),
        os.path.join(home, ".bash_profile"),
        os.path.join(home, ".bashrc"),
        os.path.join(home, ".profile"),
    ]
    if any(contains(f) for f in known_files):
        return []

    if "zsh" in shell:
        candidates = [os.path.join(home, ".zprofile"), os.path.join(home, ".zshrc")]
    elif "bash" in shell:
        candidates = [os.path.join(home, ".bash_profile"), os.path.join(home, ".bashrc")]
    else:
        candidates = [os.path.join(home, ".profile")]

    updated: list[str] = []
    if not any(os.path.exists(p) for p in candidates):
        target = candidates[0]
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "a", encoding="utf-8") as fh:
            fh.write(f'\n# Added by YPSH installer\nexport PATH="{path_dir}:$PATH"\n')
        return [target]

    for p in candidates:
        if os.path.exists(p) and not contains(p):
            with open(p, "a", encoding="utf-8") as fh:
                fh.write(f'\n# Added by YPSH installer\nexport PATH="{path_dir}:$PATH"\n')
            updated.append(p)
    return updated


def _add_to_path_windows(path_dir: str) -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg  # type: ignore
        import ctypes

        key_path = r"Environment"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            try:
                existing, _ = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                existing = ""
            parts = [p for p in existing.split(";") if p]
            if path_dir.lower() in (p.lower() for p in parts):
                changed = False
            else:
                sep = ";" if existing and not existing.endswith(";") else ""
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, existing + sep + path_dir)
                changed = True

        if changed:
            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A
            SMTO_ABORTIFHUNG = 0x0002
            ctypes.windll.user32.SendMessageTimeoutW(
                HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment", SMTO_ABORTIFHUNG, 5000, None
            )
        return changed
    except Exception:
        return False


def add_to_user_path(path_dir: str) -> str:
    system = platform.system()
    if system in ("Darwin", "Linux"):
        updated = _add_to_path_posix(path_dir)
        if updated:
            return "PATH updated in: " + ", ".join(os.path.basename(u) for u in updated)
        return "PATH already contained install dir (or update not needed)."
    elif system == "Windows":
        ok = _add_to_path_windows(path_dir)
        return "PATH updated for current user." if ok else "PATH already contained install dir (or update failed)."
    else:
        return "PATH update not supported on this OS."


# ─────────────────────────────────────────────────────────────────────────────
# Installer
# ─────────────────────────────────────────────────────────────────────────────

def install(
    *,
    to: str,
    channel: Channel,
    custom_tag: Optional[str],
    build: BuildType,
    ignoreGatekeeper: bool,
    debug: bool,
    add_to_path_flag: bool = True,
    log_cb: Optional[Callable[[str], None]] = None,
    progress_cb: Optional[Callable[[int], None]] = None,
) -> Dict[str, Any]:
    """
    Main installation routine used by both CLI and GUI.
    """

    def log(msg: str) -> None:
        if log_cb:
            try:
                log_cb(msg)
            except Exception:
                pass
        if debug:
            print(msg)

    def setprog(v: int) -> None:
        if progress_cb:
            try:
                progress_cb(max(0, min(100, int(v))))
            except Exception:
                pass

    try:
        setprog(1)
        log("[bold]Resolving release tag…[/bold]")
        tag = custom_tag if channel == "custom" else getTagFromChannel(channel)

        if not tag:
            return {"status": "error", "desc": "Could not resolve a release tag for the selected channel."}

        info = getAutoBuildInformation(tag, build=build)
        if info.get("status") != "ok":
            return info

        gate = False if ignoreGatekeeper else info["isGatekeeperCommandRequire"]

        with tempfile.TemporaryDirectory() as tmp:
            zpath = os.path.join(tmp, "ypsh.zip")
            url = info["url"]
            log(f"Downloading: [cyan]{url}[/cyan]")

            setprog(5)
            with requests.get(url, timeout=60, stream=True) as r:
                r.raise_for_status()
                total = int(r.headers.get("Content-Length", "0")) or None
                got = 0
                chunk = 1024 * 128
                with open(zpath, "wb") as fp:
                    for data in r.iter_content(chunk_size=chunk):
                        if not data:
                            continue
                        fp.write(data)
                        got += len(data)
                        if total:
                            setprog(5 + int(65 * (got / total)))

            log("Extracting archive…")
            setprog(75)
            with zipfile.ZipFile(zpath) as zf:
                zf.extract(info["origin_filename"], tmp)

            src = os.path.join(tmp, info["origin_filename"])
            os.makedirs(to, exist_ok=True)
            dst = os.path.join(to, info["recommended_filename"])

            log(f"Installing to: {dst}")
            shutil.copy2(src, dst)
            os.chmod(dst, 0o755)
            setprog(88)

            if gate:
                log("Clearing macOS quarantine flag (Gatekeeper)…")
                passingGatekeeper(dst)

            setprog(92)

            if add_to_path_flag:
                log("Adding install directory to PATH for future sessions…")
                outcome = add_to_user_path(to)
                log(f"{outcome}")

            setprog(100)

        return {"status": "ok", "dest": to, "binary": info["recommended_filename"]}

    except requests.HTTPError as e:
        return {"status": "error", "desc": f"HTTP error: {e}"}
    except Exception as e:
        return {"status": "error", "desc": f"Unhandled error: {e}"}


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def run_cli(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="ypsh-setup",
        description="Install or update YPSH for your platform.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "Examples:\n"
            "  ypsh-setup --channel stable\n"
            "  ypsh-setup --channel maybe-stable --build nuitka\n"
            "  ypsh-setup --channel custom --tag v1.2.3 --dest ~/.ypsh/bin\n"
            "  ypsh-setup --beta  # shorthand for --channel beta\n"
        ),
    )

    ch_group = parser.add_mutually_exclusive_group()
    ch_group.add_argument("--channel", "-c", choices=["stable", "maybe-stable", "beta", "custom"],
                          help="Release channel")
    ch_group.add_argument("--stable", action="store_true", help="Use stable channel")
    ch_group.add_argument("--maybe", "--maybe-stable", dest="maybe_stable", action="store_true",
                          help="Use Maybe Stable channel")
    ch_group.add_argument("--beta", action="store_true", help="Use beta channel")

    parser.add_argument("--tag", "-t", dest="custom_tag", help="Exact release tag (required if --channel custom)")
    parser.add_argument("--dest", "--to", default=DEFAULT_DEST, help=f"Installation directory (default: {DEFAULT_DEST})")
    parser.add_argument("--build", choices=["pyinstaller", "nuitka"], default="pyinstaller",
                        help="Build type (pyinstaller | nuitka). Nuitka uses '-NUI' artifacts.")
    parser.add_argument("--ignore-gatekeeper", "--ig", action="store_true",
                        help="Do NOT clear macOS quarantine attribute")
    parser.add_argument("--no-add-path", action="store_true", help="Do not add install dir to PATH")
    parser.add_argument("--add-path", action="store_true", help="Force add install dir to PATH")
    parser.add_argument("--debug", "-v", action="store_true", help="Verbose logs")

    args = parser.parse_args(argv)

    if args.channel:
        channel: Channel = args.channel  # type: ignore
    elif args.maybe_stable:
        channel = "maybe-stable"
    elif args.beta:
        channel = "beta"
    elif args.stable:
        channel = "stable"
    else:
        channel = "stable"

    if channel == "custom" and not args.custom_tag:
        parser.error("--channel custom requires --tag <version>")

    add_path_flag = True
    if args.no_add_path:
        add_path_flag = False
    if args.add_path:
        add_path_flag = True

    res = install(
        to=os.path.expanduser(args.dest),
        channel=channel,
        custom_tag=args.custom_tag,
        build=args.build,
        ignoreGatekeeper=args.ignore_gatekeeper,
        debug=args.debug,
        add_to_path_flag=add_path_flag,
        log_cb=lambda s: print(s),
        progress_cb=None,
    )
    if res.get("status") == "ok":
        print(f"[green]Installation successful[/green] → {res.get('dest')}")
        bin_name = res.get("binary", "ypsh")
        abs_cmd = os.path.join(res.get("dest", DEFAULT_DEST), bin_name)
        print(f"Run: [cyan]{abs_cmd}[/cyan]")
    else:
        print(f"[red]Failed:[/red] {res.get('desc')}")


# ─────────────────────────────────────────────────────────────────────────────
# GUI (PySide6)
# ─────────────────────────────────────────────────────────────────────────────

try:
    from PySide6.QtCore import Qt, QThread, Signal, Slot, QObject
    from PySide6.QtGui import QPalette, QColor, QPixmap, QIcon
    from PySide6.QtWidgets import (
        QApplication,
        QWizard,
        QWizardPage,
        QLabel,
        QTextEdit,
        QLineEdit,
        QVBoxLayout,
        QHBoxLayout,
        QPushButton,
        QRadioButton,
        QButtonGroup,
        QFileDialog,
        QProgressBar,
        QCheckBox,
        QWidget,
        QSpacerItem,
        QSizePolicy,
        QStyleFactory,
        QMessageBox,
        QListWidget,
        QListWidgetItem,
        QFormLayout,
        QFrame,
        QComboBox,
    )
    PYSIDE_AVAILABLE = True
except ModuleNotFoundError:
    PYSIDE_AVAILABLE = False


@dataclass
class WizardState:
    channel: Channel = "stable"
    custom_tag: Optional[str] = None
    build: BuildType = "pyinstaller"
    dest: str = DEFAULT_DEST
    add_path: bool = True
    ignore_gatekeeper: bool = False
    debug: bool = False


if PYSIDE_AVAILABLE:

    class I18n(QObject):
        languageChanged = Signal()

        def __init__(self, lang: str = "en"):
            super().__init__()
            self.lang = lang
            self._s: dict[str, dict[str, str]] = {
                "en": {
                    "app_title": "YPSH Setup",
                    "brand": "YPSH",
                    "language": "Language",
                    "lang_en": "English",
                    "lang_ja": "日本語",

                    "welcome_title": "Welcome!",
                    "welcome_msg": "This wizard will install YPSH on your system. Click “Next” to continue.",
                    "tip_1": "No admin privileges required (user directory install)",
                    "tip_2": "Can add YPSH to your PATH automatically",
                    "tip_3": "On macOS, quarantine (Gatekeeper) can be cleared",

                    "license_title": "License Agreement",
                    "license_reload": "Reload",
                    "license_accept": "I accept the license terms",
                    "license_loading": "Fetching license text…",
                    "license_error": "Failed to fetch license.\nClick “Reload” to try again.\n\n{err}",

                    "channel_title": "Choose a Release Channel",
                    "stable": "Stable",
                    "maybe_stable": "Maybe Stable",
                    "beta": "Beta",
                    "custom": "Custom",
                    "channel_hint": "If you choose Custom, you'll enter an exact tag on the next page.",

                    "build_title": "Choose Build Type",
                    "build_hint": "The Dual Build Type is now available in the NABS build system. (PyYPSH v9.0 and later)",
                    "build_py": "PyInstaller (DGC-AutoBuild V4/NABS)",
                    "build_nui": "Nuitka (DGC-AutoBuild V2-3/NABS)",

                    "custom_title": "Specify Custom Tag",
                    "custom_label": "Tag:",
                    "custom_placeholder": "e.g., v1.2.3",
                    "custom_note": "Enter an exact release tag.",

                    "dest_title": "Choose Installation Directory",
                    "browse": "Browse…",
                    "dest_note": "If the folder does not exist, it will be created.",

                    "options_title": "Advanced Options",
                    "opt_path": "Add YPSH folder to PATH (recommended)",
                    "opt_gate": "Do not clear Gatekeeper quarantine (macOS)",
                    "opt_debug": "Enable verbose logging to stdout/stderr",
                    "options_hint": "Click “Next” to review your choices.",

                    "summary_title": "Review",
                    "summary_intro": "The installer will run with the following settings:",
                    "summary_channel": "- Channel: {channel}",
                    "summary_tag": "- Tag: {tag}",
                    "summary_build": "- Build: {build}",
                    "summary_dest": "- Destination: {dest}",
                    "summary_addpath": "- Add to PATH: {yn}",
                    "summary_gate": "- Gatekeeper quarantine removal: {gate}",
                    "summary_debug": "- Debug: {dbg}",
                    "yes": "Yes",
                    "no": "No",
                    "gate_do": "Remove when needed",
                    "gate_dont": "Do not remove",

                    "install_title": "Installing…",
                    "install_logs_ph": "Logs will appear here…",
                    "install_failed": "Installation failed",
                    "error_unknown": "Unknown error",

                    "finish_title": "Hello, World!",
                    "finish_msg": "YPSH has been installed. Happy Hacking!\nDestination: {dest}",
                    "finish_open": "Open install folder",
                    "finish_copy": "Copy launch command",
                    "finish_hint": "Open a new terminal to pick up PATH changes.",
                    "copied_title": "Copied",
                    "copied_body": "Copied the following command to clipboard:\n{cmd}",

                    "btn_next": "Next",
                    "btn_back": "Back",
                    "btn_cancel": "Cancel",
                    "btn_finish": "Finish",
                },
                "ja": {
                    "app_title": "YPSH セットアップ",
                    "brand": "YPSH",
                    "language": "言語",
                    "lang_en": "English",
                    "lang_ja": "日本語",

                    "welcome_title": "ようこそ！",
                    "welcome_msg": "このウィザードでは PyYPSH をインストール/アップデートできます。「次へ」を押してください。",
                    "tip_1": "管理者権限は不要（ユーザーディレクトリにインストール）",
                    "tip_2": "PATH 環境変数への自動追加に対応",
                    "tip_3": "macOS では隔離属性（Gatekeeper）を解除可能",

                    "license_title": "ライセンスに同意",
                    "license_reload": "再読み込み",
                    "license_accept": "ライセンスに同意します",
                    "license_loading": "ライセンス文を取得中…",
                    "license_error": "ライセンスの取得に失敗しました。「再読み込み」で再試行してください。\n\n{err}",

                    "channel_title": "リリースチャンネルを選択",
                    "stable": "Stable",
                    "maybe_stable": "Maybe Stable",
                    "beta": "Beta",
                    "custom": "その他",
                    "channel_hint": "“その他”を選ぶと次ページで正確なタグを入力します。",

                    "build_title": "ビルドタイプを選択",
                    "build_hint": "NABSビルドシステムでデュアルビルドタイプが利用可能になりました。(PyYPSH v9.0以降で対応)",
                    "build_py": "PyInstaller (DGC-AutoBuild V4/NABS)",
                    "build_nui": "Nuitka (DGC-AutoBuild V2-3/NABS)",

                    "custom_title": "カスタムタグの指定",
                    "custom_label": "タグ:",
                    "custom_placeholder": "例: v1.2.3",
                    "custom_note": "正確なリリースタグを入力してください。",

                    "dest_title": "インストール先を選択",
                    "browse": "参照…",
                    "dest_note": "存在しない場合はフォルダが作成されます。",

                    "options_title": "オプション",
                    "opt_path": "YPSHフォルダをPATH環境変数に追加（推奨）",
                    "opt_gate": "Gatekeeper の隔離属性を解除しない（macOS）",
                    "opt_debug": "stdout/stderrへの詳細ログを有効化",
                    "options_hint": "「次へ」で内容を確認できます。",

                    "summary_title": "内容の確認",
                    "summary_intro": "以下の設定でインストールを実行します。",
                    "summary_channel": "- チャンネル: {channel}",
                    "summary_tag": "- タグ: {tag}",
                    "summary_build": "- ビルド: {build}",
                    "summary_dest": "- インストール先: {dest}",
                    "summary_addpath": "- PATH に追加: {yn}",
                    "summary_gate": "- Gatekeeper 解除: {gate}",
                    "summary_debug": "- デバッグ: {dbg}",
                    "yes": "はい",
                    "no": "いいえ",
                    "gate_do": "する（必要時）",
                    "gate_dont": "しない",

                    "install_title": "インストールの進行状況",
                    "install_logs_ph": "ここにログが表示されます…",
                    "install_failed": "インストール失敗",
                    "error_unknown": "不明なエラー",

                    "finish_title": "Hello, World!",
                    "finish_msg": "YPSH のインストールが完了しました。ようこそ！\nインストール先: {dest}",
                    "finish_open": "インストール先を開く",
                    "finish_copy": "起動コマンドをコピー",
                    "finish_hint": "新しいターミナルを開くと PATH の更新が反映されます。",
                    "copied_title": "コピーしました",
                    "copied_body": "次のコマンドをクリップボードにコピーしました:\n{cmd}",

                    "btn_next": "次へ",
                    "btn_back": "戻る",
                    "btn_cancel": "キャンセル",
                    "btn_finish": "完了",
                },
            }

        def t(self, key: str, **kw) -> str:
            s = self._s.get(self.lang, {}).get(key, key)
            return s.format(**kw)

        def set_lang(self, lang: str) -> None:
            if lang not in self._s:
                return
            if lang != self.lang:
                self.lang = lang
                self.languageChanged.emit()


    # ── Workers ────────────────────────────────────────────────────────────

    class LicenseWorker(QThread):
        done = Signal(str, bool, str)

        def __init__(self, url: str):
            super().__init__()
            self.url = url

        def run(self) -> None:
            try:
                r = requests.get(self.url, timeout=10)
                r.raise_for_status()
                self.done.emit(r.text, True, "")
            except Exception as e:
                self.done.emit("", False, str(e))


    class InstallWorker(QThread):
        log = Signal(str)
        progress = Signal(int)
        finished = Signal(dict)

        def __init__(self, state: WizardState):
            super().__init__()
            self.state = state

        def run(self) -> None:
            self.log.emit("Installation started…")
            try:
                out = install(
                    to=self.state.dest,
                    channel=self.state.channel,
                    custom_tag=self.state.custom_tag,
                    build=self.state.build,
                    ignoreGatekeeper=self.state.ignore_gatekeeper,
                    debug=self.state.debug,
                    add_to_path_flag=self.state.add_path,
                    log_cb=self.log.emit,
                    progress_cb=self.progress.emit,
                )
                ok = out.get("status") == "ok"
                self.log.emit("Finished: " + ("SUCCESS" if ok else "FAIL"))
            except Exception:
                out = {"status": "error", "desc": "Unhandled"}
                self.log.emit(traceback.format_exc())
            self.finished.emit(out)


    # ── UI Utils & Style ───────────────────────────────────────────────────

    def apply_dark_palette(app: QApplication) -> None:
        try:
            app.setStyle(QStyleFactory.create("Fusion"))
        except Exception:
            pass

        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#000000"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#000000"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#0a0a0a"))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#000000"))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#ffffff"))

        palette.setColor(QPalette.ColorRole.Text, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#ffffff"))

        palette.setColor(QPalette.ColorRole.Button, QColor("#111111"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#000000"))

        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#888888"))
        app.setPalette(palette)

    BASE_QSS = """
    * { font-size: 14px; }
    QWizard { background: #000000; }
    QWizard QWidget { color: #ffffff; }

    QLabel#Brand {
        font-size: 36px; font-weight: 800; color: #ffffff;
        letter-spacing: .5px; margin: 4px 0 12px 0;
    }

    QWizardPage {
        background: #000000;
        border: 1px solid #333333; border-radius: 12px;
        padding: 16px; margin: 12px;
    }

    QLineEdit, QTextEdit, QComboBox, QListWidget {
        background: #000000;
        color: #ffffff;
        border: 1px solid #333333; border-radius: 8px;
        padding: 8px;
        selection-background-color: #ffffff;
        selection-color: #000000;
    }

    QCheckBox, QRadioButton { spacing: 8px; color: #ffffff; }

    QPushButton {
        border-radius: 10px;
        padding: 8px 14px;
        background: #000000;
        color: #ffffff;
        border: 1px solid #444444;
    }
    QPushButton:hover { background: #111111; }
    QPushButton:disabled { background: #0a0a0a; color: #666666; border: 1px solid #222222; }

    QProgressBar {
        background: #000000;
        border: 1px solid #333333; border-radius: 8px; text-align: center;
        color: #ffffff;
    }
    QProgressBar::chunk { background-color: #ffffff; border-radius: 8px; margin: 1px; }

    QFrame#line { background: #333333; min-height: 1px; max-height: 1px; }
    """

    # ── Common base page ───────────────────────────────────────────────────

    class StyledPage(QWizardPage):
        def __init__(self, i18n: I18n, title_key: str = ""):
            super().__init__()
            self.i18n = i18n
            self._title_key = title_key
            self.i18n.languageChanged.connect(self._apply_title)
            self._apply_title()

        def _apply_title(self):
            if self._title_key:
                self.setTitle(self.i18n.t(self._title_key))

        def apply_texts(self):
            pass

    class LanguageSwitcher(QWidget):
        def __init__(self, i18n: I18n, parent=None):
            super().__init__(parent)
            self.i18n = i18n
            lay = QHBoxLayout(self)
            lay.setContentsMargins(0, 0, 0, 0)
            self.lbl = QLabel()
            self.cmb = QComboBox()
            self.cmb.addItem("English", "en")
            self.cmb.addItem("日本語", "ja")
            self.cmb.setCurrentIndex(0)
            self.cmb.currentIndexChanged.connect(self._on_changed)
            lay.addStretch(1)
            lay.addWidget(self.lbl)
            lay.addWidget(self.cmb)
            self.i18n.languageChanged.connect(self._apply)
            self._apply()

        def _on_changed(self, idx: int):
            self.i18n.set_lang(self.cmb.currentData())

        def _apply(self):
            self.lbl.setText(self.i18n.t("language"))
            self.cmb.blockSignals(True)
            self.cmb.setItemText(0, self.i18n.t("lang_en"))
            self.cmb.setItemText(1, self.i18n.t("lang_ja"))
            self.cmb.blockSignals(False)

    # ── Pages ───────────────────────────────────────────────────────────────

    class WelcomePage(StyledPage):
        def __init__(self, i18n: I18n):
            super().__init__(i18n, "welcome_title")
            v = QVBoxLayout(self)
            v.addWidget(LanguageSwitcher(i18n))

            brand = QLabel()
            brand.setObjectName("Brand")
            brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.msg = QLabel()
            self.msg.setWordWrap(True)
            self.msg.setAlignment(Qt.AlignmentFlag.AlignCenter)

            v.addWidget(brand)
            v.addWidget(self.msg)
            v.addItem(QSpacerItem(0, 8, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

            tips = QListWidget()
            tips.setFrameShape(QFrame.Shape.NoFrame)
            tips.setSpacing(4)
            self._tips = tips
            v.addWidget(tips)

            self._brand = brand
            self.i18n.languageChanged.connect(self.apply_texts)
            self.apply_texts()

        def apply_texts(self):
            self._brand.setText(self.i18n.t("brand"))
            self.msg.setText(self.i18n.t("welcome_msg"))
            self._tips.clear()
            for t in ["tip_1", "tip_2", "tip_3"]:
                QListWidgetItem(f"• {self.i18n.t(t)}", self._tips)

    class LicensePage(StyledPage):
        LICENSE_URL = "https://ypsh-dgc.github.io/YPSH/LICENSE"

        def __init__(self, i18n: I18n):
            super().__init__(i18n, "license_title")
            self.worker: Optional[LicenseWorker] = None

            v = QVBoxLayout(self)
            v.addWidget(LanguageSwitcher(i18n))

            self.reload_btn = QPushButton()
            self.reload_btn.clicked.connect(self._reload)

            top = QHBoxLayout()
            top.addStretch(1)
            top.addWidget(self.reload_btn)
            v.addLayout(top)

            self.view = QTextEdit()
            self.view.setReadOnly(True)
            v.addWidget(self.view, 1)

            self.chk_accept = QCheckBox()
            self.chk_accept.stateChanged.connect(self.completeChanged)
            v.addWidget(self.chk_accept)

            self.i18n.languageChanged.connect(self.apply_texts)
            self.apply_texts()

        def initializePage(self) -> None:
            self._reload()

        def isComplete(self) -> bool:
            return self.chk_accept.isChecked() and bool(self.view.toPlainText().strip())

        @Slot()
        def _reload(self) -> None:
            self.setEnabled(False)
            self.view.setPlainText(self.i18n.t("license_loading"))
            self.worker = LicenseWorker(self.LICENSE_URL)
            self.worker.done.connect(self._on_done)
            self.worker.start()

        @Slot(str, bool, str)
        def _on_done(self, text: str, ok: bool, err: str) -> None:
            self.setEnabled(True)
            if ok:
                self.view.setPlainText(text)
            else:
                self.view.setPlainText(self.i18n.t("license_error", err=err))
                QMessageBox.warning(self, self.i18n.t("license_title"), self.i18n.t("license_error", err=err))
            self.completeChanged.emit()

        def apply_texts(self):
            self.reload_btn.setText(self.i18n.t("license_reload"))
            self.chk_accept.setText(self.i18n.t("license_accept"))
            if not self.view.toPlainText().strip():
                self.view.setPlaceholderText(self.i18n.t("license_loading"))

    class ChannelPage(StyledPage):
        def __init__(self, i18n: I18n, state: WizardState):
            super().__init__(i18n, "channel_title")
            self.state = state
            v = QVBoxLayout(self)
            v.addWidget(LanguageSwitcher(i18n))

            self.grp = QButtonGroup(self)
            self.rad_stable = QRadioButton()
            self.rad_maybe = QRadioButton()
            self.rad_beta = QRadioButton()
            self.rad_custom = QRadioButton()
            self.rad_stable.setChecked(True)

            for i, w in enumerate([self.rad_stable, self.rad_maybe, self.rad_beta, self.rad_custom]):
                self.grp.addButton(w, i)
                v.addWidget(w)

            self.hint = QLabel()
            self.hint.setWordWrap(True)
            v.addWidget(self.hint)

            self.i18n.languageChanged.connect(self.apply_texts)
            self.apply_texts()

        def validatePage(self) -> bool:
            if self.rad_stable.isChecked():
                self.state.channel = "stable"
            elif self.rad_maybe.isChecked():
                self.state.channel = "maybe-stable"
            elif self.rad_beta.isChecked():
                self.state.channel = "beta"
            else:
                self.state.channel = "custom"
            return True

        def nextId(self) -> int:
            wiz: InstallerWizard = self.wizard()  # type: ignore
            return wiz.Page_CustomTag if self.rad_custom.isChecked() else wiz.Page_Build

        def apply_texts(self):
            self.rad_stable.setText(self.i18n.t("stable"))
            self.rad_maybe.setText(self.i18n.t("maybe_stable"))
            self.rad_beta.setText(self.i18n.t("beta"))
            self.rad_custom.setText(self.i18n.t("custom"))
            self.hint.setText(self.i18n.t("channel_hint"))

    class CustomTagPage(StyledPage):
        def __init__(self, i18n: I18n, state: WizardState):
            super().__init__(i18n, "custom_title")
            self.state = state
            v = QVBoxLayout(self)
            v.addWidget(LanguageSwitcher(i18n))

            form = QFormLayout()
            self.lbl = QLabel()
            self.edit = QLineEdit()
            form.addRow(self.lbl, self.edit)
            v.addLayout(form)

            self.note = QLabel()
            self.note.setWordWrap(True)
            v.addWidget(self.note)

            self.i18n.languageChanged.connect(self.apply_texts)
            self.apply_texts()
            self.edit.textChanged.connect(self.completeChanged)

        def isComplete(self) -> bool:
            return bool(self.edit.text().strip())

        def validatePage(self) -> bool:
            self.state.custom_tag = self.edit.text().strip()
            return True

        def nextId(self) -> int:
            return self.wizard().Page_Build  # type: ignore

        def apply_texts(self):
            self.lbl.setText(self.i18n.t("custom_label"))
            self.edit.setPlaceholderText(self.i18n.t("custom_placeholder"))
            self.note.setText(self.i18n.t("custom_note"))

    class BuildTypePage(StyledPage):
        def __init__(self, i18n: I18n, state: WizardState):
            super().__init__(i18n, "build_title")
            self.state = state
            v = QVBoxLayout(self)
            v.addWidget(LanguageSwitcher(i18n))

            self.grp = QButtonGroup(self)
            self.rad_py = QRadioButton()
            self.rad_nui = QRadioButton()
            self.rad_py.setChecked(True)

            self.grp.addButton(self.rad_py)
            self.grp.addButton(self.rad_nui)
            v.addWidget(self.rad_py)
            v.addWidget(self.rad_nui)

            self.hint = QLabel()
            self.hint.setWordWrap(True)
            v.addWidget(self.hint)

            self.i18n.languageChanged.connect(self.apply_texts)
            self.apply_texts()

        def validatePage(self) -> bool:
            self.state.build = "nuitka" if self.rad_nui.isChecked() else "pyinstaller"
            return True

        def nextId(self) -> int:
            return self.wizard().Page_Destination  # type: ignore

        def apply_texts(self):
            self.rad_py.setText(self.i18n.t("build_py"))
            self.rad_nui.setText(self.i18n.t("build_nui"))
            self.hint.setText(self.i18n.t("build_hint"))

    class DestinationPage(StyledPage):
        def __init__(self, i18n: I18n, state: WizardState):
            super().__init__(i18n, "dest_title")
            self.state = state
            v = QVBoxLayout(self)
            v.addWidget(LanguageSwitcher(i18n))

            row = QHBoxLayout()
            self.edit = QLineEdit(DEFAULT_DEST)
            self.btn = QPushButton()
            self.btn.clicked.connect(self._browse)
            row.addWidget(self.edit, 1)
            row.addWidget(self.btn)
            v.addLayout(row)

            self.note = QLabel()
            self.note.setWordWrap(True)
            v.addWidget(self.note)

            self.i18n.languageChanged.connect(self.apply_texts)
            self.apply_texts()

        @Slot()
        def _browse(self) -> None:
            d = QFileDialog.getExistingDirectory(self, self.i18n.t("dest_title"), self.edit.text())
            if d:
                self.edit.setText(d)

        def validatePage(self) -> bool:
            self.state.dest = self.edit.text().strip() or DEFAULT_DEST
            return True

        def nextId(self) -> int:
            return self.wizard().Page_Options  # type: ignore

        def apply_texts(self):
            self.btn.setText(self.i18n.t("browse"))
            self.note.setText(self.i18n.t("dest_note"))

    class OptionsPage(StyledPage):
        def __init__(self, i18n: I18n, state: WizardState):
            super().__init__(i18n, "options_title")
            self.state = state
            v = QVBoxLayout(self)
            v.addWidget(LanguageSwitcher(i18n))

            self.chk_path = QCheckBox()
            self.chk_path.setChecked(True)
            self.chk_gate = QCheckBox()
            self.chk_gate.setChecked(False)
            self.chk_dbg = QCheckBox()
            self.chk_dbg.setChecked(False)

            v.addWidget(self.chk_path)
            v.addWidget(self.chk_gate)
            v.addWidget(self.chk_dbg)

            v.addWidget(self._hline())
            self.hint = QLabel()
            self.hint.setWordWrap(True)
            v.addWidget(self.hint)

            self.i18n.languageChanged.connect(self.apply_texts)
            self.apply_texts()

        def _hline(self) -> QFrame:
            line = QFrame()
            line.setObjectName("line")
            line.setFrameShape(QFrame.Shape.HLine)
            line.setFrameShadow(QFrame.Shadow.Sunken)
            return line

        def validatePage(self) -> bool:
            self.state.add_path = self.chk_path.isChecked()
            self.state.ignore_gatekeeper = self.chk_gate.isChecked()
            self.state.debug = self.chk_dbg.isChecked()
            return True

        def nextId(self) -> int:
            return self.wizard().Page_Summary  # type: ignore

        def apply_texts(self):
            self.chk_path.setText(self.i18n.t("opt_path"))
            self.chk_gate.setText(self.i18n.t("opt_gate"))
            self.chk_dbg.setText(self.i18n.t("opt_debug"))
            self.hint.setText(self.i18n.t("options_hint"))

    class SummaryPage(StyledPage):
        def __init__(self, i18n: I18n, state: WizardState):
            super().__init__(i18n, "summary_title")
            self.state = state
            self.view = QTextEdit()
            self.view.setReadOnly(True)
            v = QVBoxLayout(self)
            v.addWidget(LanguageSwitcher(i18n))
            v.addWidget(self.view)
            self.i18n.languageChanged.connect(self.apply_texts)

        def initializePage(self) -> None:
            self.apply_texts()

        def nextId(self) -> int:
            return self.wizard().Page_Install  # type: ignore

        def apply_texts(self):
            lines = [self.i18n.t("summary_intro"), ""]
            lines.append(self.i18n.t("summary_channel", channel=self.state.channel))
            if self.state.channel == "custom" and self.state.custom_tag:
                lines.append(self.i18n.t("summary_tag", tag=self.state.custom_tag))
            lines.append(self.i18n.t("summary_build", build=self.state.build))
            lines.append(self.i18n.t("summary_dest", dest=self.state.dest))
            lines.append(self.i18n.t("summary_addpath", yn=self.i18n.t("yes") if self.state.add_path else self.i18n.t("no")))
            gate_txt = self.i18n.t("gate_dont") if self.state.ignore_gatekeeper else self.i18n.t("gate_do")
            lines.append(self.i18n.t("summary_gate", gate=gate_txt))
            lines.append(self.i18n.t("summary_debug", dbg=self.i18n.t("yes") if self.state.debug else self.i18n.t("no")))
            self.view.setPlainText("\n".join(lines))

    class InstallPage(StyledPage):
        def __init__(self, i18n: I18n, state: WizardState):
            super().__init__(i18n, "install_title")
            self.state = state
            self.worker: Optional[InstallWorker] = None

            v = QVBoxLayout(self)
            v.addWidget(LanguageSwitcher(i18n))

            self.prg = QProgressBar()
            self.prg.setRange(0, 100)
            self.log = QTextEdit()
            self.log.setReadOnly(True)

            v.addWidget(self.prg)
            v.addWidget(self.log, 1)

            self.i18n.languageChanged.connect(self.apply_texts)
            self.apply_texts()

        def initializePage(self) -> None:
            wiz: InstallerWizard = self.wizard()  # type: ignore
            for btn in (QWizard.WizardButton.BackButton, QWizard.WizardButton.NextButton):
                w = wiz.button(btn)
                if w:
                    w.setEnabled(False)

            self.worker = InstallWorker(self.state)
            self.worker.log.connect(self.log.append)
            self.worker.progress.connect(self.prg.setValue)
            self.worker.finished.connect(self._done)
            self.worker.start()

        @Slot(dict)
        def _done(self, res: Dict[str, Any]) -> None:
            wiz: InstallerWizard = self.wizard()  # type: ignore
            ok = res.get("status") == "ok"
            self.prg.setValue(100)
            if ok:
                wiz.setProperty("result", res)
                nxt = wiz.button(QWizard.WizardButton.NextButton)
                if nxt:
                    nxt.setEnabled(True)
                    nxt.click()
            else:
                back = wiz.button(QWizard.WizardButton.BackButton)
                if back:
                    back.setEnabled(True)
                cancel = wiz.button(QWizard.WizardButton.CancelButton)
                if cancel:
                    cancel.setEnabled(True)
                    cancel.setVisible(True)
                QMessageBox.critical(self, self.i18n.t("install_failed"), res.get("desc", self.i18n.t("error_unknown")))

        def nextId(self) -> int:
            return self.wizard().Page_Finish  # type: ignore

        def apply_texts(self):
            self.log.setPlaceholderText(self.i18n.t("install_logs_ph"))

    class FinishPage(StyledPage):
        def __init__(self, i18n: I18n, state: WizardState):
            super().__init__(i18n, "finish_title")
            self.state = state
            v = QVBoxLayout(self)
            v.addWidget(LanguageSwitcher(i18n))

            self.msg = QLabel()
            self.msg.setWordWrap(True)
            v.addWidget(self.msg)

            row = QHBoxLayout()
            row.addStretch(1)
            self.btn_open = QPushButton()
            self.btn_copy_cmd = QPushButton()
            row.addWidget(self.btn_open)
            row.addWidget(self.btn_copy_cmd)
            v.addLayout(row)

            self.hint = QLabel()
            self.hint.setWordWrap(True)
            v.addWidget(self.hint)

            self.btn_open.clicked.connect(self._open_folder)
            self.btn_copy_cmd.clicked.connect(self._copy_cmd)

            self.i18n.languageChanged.connect(self.apply_texts)

        def initializePage(self) -> None:
            self.apply_texts()

        @Slot()
        def _open_folder(self) -> None:
            dest = self.state.dest
            if platform.system() == "Windows":
                os.startfile(dest)  # type: ignore
            elif platform.system() == "Darwin":
                os.system(f'open "{dest}"')
            else:
                os.system(f'xdg-open "{dest}"')

        @Slot()
        def _copy_cmd(self) -> None:
            bin_name = "ypsh.exe" if platform.system() == "Windows" else "ypsh"
            cmd = os.path.join(self.state.dest, bin_name)
            QApplication.clipboard().setText(cmd)
            QMessageBox.information(self, self.i18n.t("copied_title"), self.i18n.t("copied_body", cmd=cmd))

        def isFinalPage(self) -> bool:
            return True

        def apply_texts(self):
            dest = self.state.dest
            wiz = self.wizard()
            if wiz is not None:
                res = wiz.property("result")
                if isinstance(res, dict):
                    dest = res.get("dest", dest)

            self.setTitle(self.i18n.t("finish_title"))
            self.msg.setText(self.i18n.t("finish_msg", dest=dest))
            self.btn_open.setText(self.i18n.t("finish_open"))
            self.btn_copy_cmd.setText(self.i18n.t("finish_copy"))
            self.hint.setText(self.i18n.t("finish_hint"))

    class InstallerWizard(QWizard):
        Page_Welcome, Page_License, Page_Channel, Page_CustomTag, Page_Build, Page_Destination, Page_Options, Page_Summary, Page_Install, Page_Finish = range(10)

        def __init__(self):
            super().__init__()
            self.i18n = I18n(lang="en")
            self.state = WizardState()

            self.setWindowTitle(self.i18n.t("app_title"))
            self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
            self.setMinimumSize(760, 560)
            self.setPixmap(QWizard.WizardPixmap.WatermarkPixmap, QPixmap())
            self.setPixmap(QWizard.WizardPixmap.LogoPixmap, QPixmap())
            self.setWindowIcon(QIcon())

            self.setPage(self.Page_Welcome, WelcomePage(self.i18n))
            self.setPage(self.Page_License, LicensePage(self.i18n))
            self.setPage(self.Page_Channel, ChannelPage(self.i18n, self.state))
            self.setPage(self.Page_CustomTag, CustomTagPage(self.i18n, self.state))
            self.setPage(self.Page_Build, BuildTypePage(self.i18n, self.state))
            self.setPage(self.Page_Destination, DestinationPage(self.i18n, self.state))
            self.setPage(self.Page_Options, OptionsPage(self.i18n, self.state))
            self.setPage(self.Page_Summary, SummaryPage(self.i18n, self.state))
            self.setPage(self.Page_Install, InstallPage(self.i18n, self.state))
            self.setPage(self.Page_Finish, FinishPage(self.i18n, self.state))

            self.setButtonLayout([
                QWizard.WizardButton.Stretch,
                QWizard.WizardButton.CancelButton,
                QWizard.WizardButton.BackButton,
                QWizard.WizardButton.NextButton,
                QWizard.WizardButton.FinishButton,
            ])

            self._apply_button_texts()
            self.setStyleSheet(BASE_QSS)
            self.i18n.languageChanged.connect(self._apply_i18n_all)

        def _apply_button_texts(self):
            self.setButtonText(QWizard.WizardButton.NextButton, self.i18n.t("btn_next"))
            self.setButtonText(QWizard.WizardButton.BackButton, self.i18n.t("btn_back"))
            self.setButtonText(QWizard.WizardButton.CancelButton, self.i18n.t("btn_cancel"))
            self.setButtonText(QWizard.WizardButton.FinishButton, self.i18n.t("btn_finish"))

        @Slot()
        def _apply_i18n_all(self):
            self.setWindowTitle(self.i18n.t("app_title"))
            self._apply_button_texts()

        def nextId(self) -> int:
            cur = self.currentId()
            if cur == self.Page_Welcome:
                return self.Page_License
            if cur == self.Page_License:
                return self.Page_Channel
            if cur == self.Page_Channel:
                return super().nextId()
            if cur == self.Page_CustomTag:
                return self.Page_Build
            if cur == self.Page_Build:
                return self.Page_Destination
            if cur == self.Page_Destination:
                return self.Page_Options
            if cur == self.Page_Options:
                return self.Page_Summary
            if cur == self.Page_Summary:
                return self.Page_Install
            if cur == self.Page_Install:
                return self.Page_Finish
            return -1

    def launch_gui() -> None:
        app = QApplication(sys.argv)
        apply_dark_palette(app)
        w = InstallerWizard()
        w.show()
        sys.exit(app.exec())

else:
    def launch_gui() -> None:
        print("[yellow]PySide6 not found; using CLI.[/yellow]")
        run_cli([a for a in sys.argv[1:] if a != "gui"])


# ─────────────────────────────────────────────────────────────────────────────
# Entry
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    argv = sys.argv[1:]
    if "cli" in argv or not PYSIDE_AVAILABLE:
        if "cli" in argv:
            argv.remove("cli")
        run_cli(argv)
    else:
        launch_gui()
