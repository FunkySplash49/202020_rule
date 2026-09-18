"""py2app build config for TwentyTwenty.

Build a standalone app bundle:

    .venv/bin/python setup.py py2app

The result is dist/TwentyTwenty.app, which runs without the venv. For a fast
development build that symlinks back to this source tree (so edits show up on
the next launch, but the bundle is NOT distributable), use:

    .venv/bin/python setup.py py2app -A

AUTO-LAUNCH AT LOGIN (not implemented in code, it's a one-time manual step):
copy dist/TwentyTwenty.app to /Applications, then go to
System Settings -> General -> Login Items & Extensions -> "Open at Login" ->
click + -> pick TwentyTwenty.app. Because LSUIElement is set below, it starts
silently in the menu bar with no Dock icon and no window.
"""

from setuptools import setup

APP = ["twenty.py"]

OPTIONS = {
    "argv_emulation": False,  # must stay off: it blocks startup for menu bar apps
    "packages": ["rumps"],
    "includes": ["overlay"],
    "plist": {
        "CFBundleName": "TwentyTwenty",
        "CFBundleDisplayName": "TwentyTwenty",
        "CFBundleIdentifier": "com.example.twentytwenty",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1.0.0",
        "LSUIElement": True,  # menu bar only: no Dock icon, no app switcher entry
        "NSHumanReadableCopyright": "",
    },
}

setup(
    name="TwentyTwenty",
    app=APP,
    data_files=[],
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
