#!/bin/bash

# Variables
APP_NAME="Affentanz"
APP_PATH="/Users/martin/PycharmProjects/Affentanz/dist/${APP_NAME}.app"
DMG_PATH="/Users/martin/PycharmProjects/Affentanz/dist/${APP_NAME}.dmg"
DMG_TEMP_PATH="/Users/martin/PycharmProjects/Affentanz/dist/${APP_NAME}_temp.dmg"
DMG_VOLUME_NAME="${APP_NAME} Installer"
DMG_SIZE="500m"

# Make sure our destination directory exists
mkdir -p "/Users/martin/PycharmProjects/Affentanz/dist"

# Create a temporary DMG
hdiutil create -srcfolder "$APP_PATH" -volname "$DMG_VOLUME_NAME" -fs HFS+ \
      -fsargs "-c c=64,a=16,e=16" -format UDRW -size "$DMG_SIZE" "$DMG_TEMP_PATH"

# Mount the temporary DMG
MOUNT_POINT=$(hdiutil attach -readwrite -noverify -noautoopen "$DMG_TEMP_PATH" | \
         grep -E '^/dev/' | sed 1q | awk '{print $3}')

# Add a link to the Applications folder
ln -s /Applications "$MOUNT_POINT/Applications"

# Optional: Set the window style
echo '
   tell application "Finder"
     tell disk "'$DMG_VOLUME_NAME'"
           open
           set current view of container window to icon view
           set toolbar visible of container window to false
           set statusbar visible of container window to false
           set the bounds of container window to {400, 100, 920, 440}
           set position of item "'$APP_NAME.app'" of container window to {160, 205}
           set position of item "Applications" of container window to {360, 205}
           close
           open
           update without registering applications
           delay 2
     end tell
   end tell
' | osascript

# Finalize the DMG
hdiutil detach "$MOUNT_POINT"
hdiutil convert "$DMG_TEMP_PATH" -format UDZO -imagekey zlib-level=9 -o "$DMG_PATH"
rm -f "$DMG_TEMP_PATH"

echo "DMG created at: $DMG_PATH"