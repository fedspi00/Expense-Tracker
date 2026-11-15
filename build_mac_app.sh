#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Build TrackIt!.app — a proper macOS app bundle
# Run once:   bash build_mac_app.sh
# Then:       double-click TrackIt!.app  OR  drag it to /Applications
# ─────────────────────────────────────────────────────────────────────────────
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

APP_BUNDLE="$DIR/TrackIt!.app"
ICONSET="/tmp/TrackIt.iconset"

echo ""
echo "  ◈  Building TrackIt!.app"
echo "  ──────────────────────────"
echo ""

# ── 1. Activate venv ─────────────────────────────────────────────────────────
if [ ! -d "$DIR/venv" ]; then
  echo "  ✗  venv not found. Run install.sh first."
  exit 1
fi
source "$DIR/venv/bin/activate"

# ── 2. Generate .iconset PNGs ─────────────────────────────────────────────────
echo "  →  Generating icon sizes…"
rm -rf "$ICONSET"
mkdir -p "$ICONSET"

python3 - <<'PYEOF'
import sys
sys.path.insert(0, '.')
from icon import create_app_icon
import os

iconset = "/tmp/TrackIt.iconset"
pairs = [
    ("icon_16x16.png",        16),
    ("icon_16x16@2x.png",     32),
    ("icon_32x32.png",        32),
    ("icon_32x32@2x.png",     64),
    ("icon_128x128.png",     128),
    ("icon_128x128@2x.png",  256),
    ("icon_256x256.png",     256),
    ("icon_256x256@2x.png",  512),
    ("icon_512x512.png",     512),
    ("icon_512x512@2x.png", 1024),
]
for name, size in pairs:
    img = create_app_icon(size)
    img.save(os.path.join(iconset, name))
    print(f"      {name}")
PYEOF

# ── 3. Convert to .icns ───────────────────────────────────────────────────────
echo "  →  Converting to .icns…"
iconutil -c icns "$ICONSET" -o /tmp/AppIcon.icns

# ── 4. Create .app structure ─────────────────────────────────────────────────
echo "  →  Creating bundle structure…"
rm -rf "$APP_BUNDLE"
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"

cp /tmp/AppIcon.icns "$APP_BUNDLE/Contents/Resources/AppIcon.icns"

# ── 5. Info.plist ─────────────────────────────────────────────────────────────
cat > "$APP_BUNDLE/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>              <string>TrackIt!</string>
  <key>CFBundleDisplayName</key>       <string>TrackIt!</string>
  <key>CFBundleIdentifier</key>        <string>com.trackit.expense</string>
  <key>CFBundleExecutable</key>        <string>TrackIt!</string>
  <key>CFBundleVersion</key>           <string>2.0.0</string>
  <key>CFBundleShortVersionString</key><string>2.0</string>
  <key>CFBundleIconFile</key>          <string>AppIcon</string>
  <key>CFBundlePackageType</key>       <string>APPL</string>
  <key>NSHighResolutionCapable</key>   <true/>
  <key>NSPrincipalClass</key>          <string>NSApplication</string>
  <key>LSMinimumSystemVersion</key>    <string>11.0</string>
</dict>
</plist>
PLIST

# ── 6. In-bundle interpreter ──────────────────────────────────────────────────
# macOS names the Touch ID / permission prompts after the process it sees. If we
# ran the venv's python directly, every prompt would read "python3.13 is trying
# to…". Copying the interpreter INTO Contents/MacOS makes the running process
# belong to this bundle, so the system uses CFBundleDisplayName ("TrackIt!").
echo "  →  Embedding interpreter…"
REAL_PY=$(python3 -c 'import sys; print(sys._base_executable)')
BASE_PREFIX=$(python3 -c 'import sys; print(sys.base_prefix)')
SITE_PKGS=$(python3 -c 'import site; print(site.getsitepackages()[0])')

cp "$REAL_PY" "$APP_BUNDLE/Contents/MacOS/TrackIt"
chmod +x "$APP_BUNDLE/Contents/MacOS/TrackIt"

# ── 7. Launcher executable ────────────────────────────────────────────────────
LAUNCHER="$APP_BUNDLE/Contents/MacOS/TrackIt!"
# Absolute paths so the .app works from anywhere (incl. /Applications).
# PYTHONHOME points the embedded interpreter at the standard library;
# PYTHONPATH adds this project's installed packages. Keeping them as env vars
# (rather than files inside Contents/) leaves the bundle signable.
# exec => the shell is replaced, leaving the in-bundle interpreter as the process.
cat > "$LAUNCHER" <<LAUNCHER_EOF
#!/bin/bash
HERE="\$(cd "\$(dirname "\$0")" && pwd)"
export PYTHONHOME="$BASE_PREFIX"
export PYTHONPATH="$SITE_PKGS"
exec "\$HERE/TrackIt" "$DIR/main.py"
LAUNCHER_EOF
chmod +x "$LAUNCHER"

# ── 8. Ad-hoc sign so the system trusts the bundle identity ──────────────────
echo "  →  Signing bundle…"
codesign --force --sign - "$APP_BUNDLE" 2>/dev/null \
  && echo "      signed (ad-hoc)" \
  || echo "      ⚠ codesign unavailable — app still runs, prompt may show a generic name"

# ── 9. Refresh Dock cache ─────────────────────────────────────────────────────
touch "$APP_BUNDLE"
# Tell the system the icon changed
if command -v killall &>/dev/null; then
  killall Dock 2>/dev/null || true
fi

echo ""
echo "  ✅  TrackIt!.app is ready at:"
echo "      $APP_BUNDLE"
echo ""
echo "  Next steps:"
echo "  • Double-click TrackIt!.app in Finder to launch"
echo "  • Drag it to /Applications for a permanent install"
echo "  • Drag it to the Dock for one-click access"
echo ""
