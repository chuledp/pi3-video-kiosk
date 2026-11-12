#!/usr/bin/env bash
# =============================================================================
# Desinstalador de Pi 3 Video Kiosk
# =============================================================================

set -e

if [ "$EUID" -ne 0 ]; then
    echo "Elevando a permisos de root (sudo)..."
    exec sudo bash "$0" "$@"
fi

echo "Deteniendo y deshabilitando servicio pi3-video-kiosk..."
systemctl stop pi3-video-kiosk.service 2>/dev/null || true
systemctl disable pi3-video-kiosk.service 2>/dev/null || true

rm -f /etc/systemd/system/pi3-video-kiosk.service
systemctl daemon-reload

rm -rf /opt/pi3-video-kiosk
rm -rf /media/usb_kiosk

echo "✅ Pi 3 Video Kiosk desinstalado correctamente."

