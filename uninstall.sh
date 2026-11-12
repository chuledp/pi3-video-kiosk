#!/usr/bin/env bash
# =============================================================================
# Desinstalador de Pi 3 Video Kiosk
# =============================================================================

set -e

if [ "$EUID" -ne 0 ]; then
    if [ -f "$0" ] && [ "$0" != "bash" ] && [ "$0" != "-bash" ] && [ "$0" != "sh" ]; then
        echo "Elevando a permisos de root (sudo)..."
        exec sudo bash "$0" "$@"
    else
        echo "Elevando a permisos de root (sudo)..."
        exec sudo bash -c "$(curl -sSL https://raw.githubusercontent.com/chuledp/pi3-video-kiosk/main/uninstall.sh)" -- "$@"
    fi
fi

echo "Deteniendo y deshabilitando servicio pi3-video-kiosk..."
systemctl stop pi3-video-kiosk.service 2>/dev/null || true
systemctl disable pi3-video-kiosk.service 2>/dev/null || true

rm -f /etc/systemd/system/pi3-video-kiosk.service
systemctl daemon-reload

rm -rf /opt/pi3-video-kiosk
rm -rf /media/usb_kiosk

echo "✅ Pi 3 Video Kiosk desinstalado correctamente."

