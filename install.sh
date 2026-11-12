#!/usr/bin/env bash
# =============================================================================
# 🚀 Instalador Automático: Pi 3 Video Kiosk Ultra-Optimizado
# =============================================================================
# Configura una Raspberry Pi 3 para reproducir video 1080p H.264 en loop
# desde cualquier pendrive USB conectado automáticamente al encender.
# =============================================================================

set -e

# Asegurar permisos de superusuario
if [ "$EUID" -ne 0 ]; then
    echo "Elevando a permisos de root (sudo)..."
    exec sudo bash "$0" "$@"
fi

echo "==========================================================="
echo "🎬 Instalando Pi 3 Video Kiosk (Modo Kiosk Headless Pendrive)"
echo "==========================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/pi3-video-kiosk"

# Detectar usuario real (por ej. 'pi')
REAL_USER="${SUDO_USER:-pi}"
REAL_HOME=$(eval echo "~$REAL_USER")

# 1. Instalar dependencias esenciales mínimas (sin entornos pesados)
echo "1/4. Instalando paquetes mínimos (mpv, alsa-utils)..."
apt update || true
apt install -y mpv alsa-utils || true

# 2. Configurar memoria de GPU (gpu_mem=128) para decodificación fluida 1080p
echo "2/4. Optimizando memoria de GPU en Raspberry Pi 3..."
CONFIG_TXT=""
if [ -f "/boot/firmware/config.txt" ]; then
    CONFIG_TXT="/boot/firmware/config.txt"
elif [ -f "/boot/config.txt" ]; then
    CONFIG_TXT="/boot/config.txt"
fi

if [ -n "$CONFIG_TXT" ]; then
    if grep -q "^gpu_mem=" "$CONFIG_TXT"; then
        sed -i 's/^gpu_mem=.*/gpu_mem=128/' "$CONFIG_TXT"
    else
        echo "gpu_mem=128" >> "$CONFIG_TXT"
    fi
    if ! grep -q "^disable_overscan=1" "$CONFIG_TXT"; then
        echo "disable_overscan=1" >> "$CONFIG_TXT"
    fi
    echo "    Memoria GPU configurada a 128 MB en $CONFIG_TXT."
fi

# Evitar suspensión de pantalla en consola (consoleblank=0)
CMDLINE_TXT=""
if [ -f "/boot/firmware/cmdline.txt" ]; then
    CMDLINE_TXT="/boot/firmware/cmdline.txt"
elif [ -f "/boot/cmdline.txt" ]; then
    CMDLINE_TXT="/boot/cmdline.txt"
fi

if [ -n "$CMDLINE_TXT" ]; then
    if ! grep -q "consoleblank=0" "$CMDLINE_TXT"; then
        sed -i 's/$/ consoleblank=0/' "$CMDLINE_TXT"
        echo "    consoleblank=0 agregado a $CMDLINE_TXT."
    fi
fi

# 3. Copiar script de ejecución a /opt/pi3-video-kiosk
echo "3/4. Instalando reproductor en $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
if [ -f "$SCRIPT_DIR/player.py" ]; then
    cp "$SCRIPT_DIR/player.py" "$INSTALL_DIR/player.py"
    cp "$SCRIPT_DIR/uninstall.sh" "$INSTALL_DIR/uninstall.sh" 2>/dev/null || true
else
    echo "    Descargando archivos desde GitHub..."
    curl -sSL "https://raw.githubusercontent.com/chuledp/pi3-video-kiosk/main/player.py" -o "$INSTALL_DIR/player.py"
    curl -sSL "https://raw.githubusercontent.com/chuledp/pi3-video-kiosk/main/uninstall.sh" -o "$INSTALL_DIR/uninstall.sh" 2>/dev/null || true
fi
chmod +x "$INSTALL_DIR/player.py" "$INSTALL_DIR/uninstall.sh" 2>/dev/null || true

mkdir -p /media/usb_kiosk

# 4. Configurar servicio systemd para arranque automático en boot
echo "4/4. Configurando servicio de arranque automático (systemd)..."
SERVICE_DST="/etc/systemd/system/pi3-video-kiosk.service"

if [ -f "$SCRIPT_DIR/pi3-video-kiosk.service" ]; then
    cp "$SCRIPT_DIR/pi3-video-kiosk.service" "$SERVICE_DST"
else
    echo "    Descargando servicio systemd desde GitHub..."
    curl -sSL "https://raw.githubusercontent.com/chuledp/pi3-video-kiosk/main/pi3-video-kiosk.service" -o "$SERVICE_DST"
fi

# Ajustar variables según el usuario real
sed -i "s|/home/pi|$REAL_HOME|g" "$SERVICE_DST"

systemctl daemon-reload
systemctl enable pi3-video-kiosk.service
systemctl restart pi3-video-kiosk.service

echo "==========================================================="
echo "✅ ¡INSTALACIÓN COMPLETADA CON ÉXITO!"
echo "==========================================================="
echo "• Enchufá cualquier Pendrive USB con tu video 1080p H.264 (.mp4)."
echo "• La Raspberry Pi 3 lo detectará y empezará a reproducir en bucle."
echo "• Si desconectás el pendrive, la pantalla queda en negro esperando."
echo "• Para ver el estado en vivo: sudo journalctl -u pi3-video-kiosk -f"
echo "==========================================================="

