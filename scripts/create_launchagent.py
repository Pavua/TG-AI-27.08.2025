from __future__ import annotations

import os
from pathlib import Path


def main() -> None:
    label = "com.ftg.userbot"
    home = Path.home()
    agents = home / "Library" / "LaunchAgents"
    agents.mkdir(parents=True, exist_ok=True)
    plist_path = agents / f"{label}.plist"

    repo_root = Path(__file__).resolve().parents[1]
    run_script = repo_root / "ftg" / "run_ftg.sh"

    plist = f"""
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>{run_script}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{repo_root}/ftg.out.log</string>
    <key>StandardErrorPath</key>
    <string>{repo_root}/ftg.err.log</string>
    <key>KeepAlive</key>
    <true/>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
""".strip()

    plist_path.write_text(plist)
    print(f"Wrote {plist_path}")
    print("Load it with: launchctl load -w " + str(plist_path))


if __name__ == "__main__":
    main()
