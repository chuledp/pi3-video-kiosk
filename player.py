#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
🎬 Pi 3 Video Kiosk • Reproductor Headless Ultra-Optimizado
=============================================================================
Diseñado para Raspberry Pi 3 (BCM2837 + VideoCore IV):
1. Detecta automáticamente cualquier Pendrive USB conectado.
2. Monta el pendrive en modo solo lectura (ro) para evitar corrupción por corte de luz.
3. Modo estricto mono-archivo: toma únicamente el primer video que encuentre.
4. Ignora archivos ocultos y metadatos de macOS (._* y .Trashes).
5. Reproducción 1080p H.264 por hardware (V4L2 M2M) con bucle infinito sin pausas.
6. Pantalla en negro silenciosa si no hay pendrive conectado.
=============================================================================
"""

import os
import sys
import time
import glob
import signal
import codecs
import shutil
import subprocess
from typing import Optional, List

VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov", ".mkv", ".avi", ".webm"}
USB_MOUNT_POINT = "/media/usb_kiosk"


def log(msg: str):
    """Muestra logs con marca de tiempo para monitoreo mediante journalctl."""
    t = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{t}] [Pi3-Kiosk] {msg}", flush=True)


def setup_display_environment():
    """Detecta y configura el entorno de pantalla dinámicamente."""
    # Buscar socket activo de servidor X11 (/tmp/.X11-unix/X0, etc.)
    x11_sockets = glob.glob("/tmp/.X11-unix/X*")
    if x11_sockets:
        disp_num = os.path.basename(x11_sockets[0]).replace("X", ":")
        os.environ.setdefault("DISPLAY", disp_num)
        for auth_candidate in [
            os.path.expanduser("~/.Xauthority"),
            "/home/pi/.Xauthority",
            "/root/.Xauthority"
        ]:
            if os.path.isfile(auth_candidate):
                os.environ.setdefault("XAUTHORITY", auth_candidate)
                break
    elif not os.environ.get("WAYLAND_DISPLAY"):
        # Modo Consola / Headless puro sin X11:
        # Remover DISPLAY para que MPV use DRM/KMS directo a framebuffer sin errores
        os.environ.pop("DISPLAY", None)
        os.environ.pop("XAUTHORITY", None)


def ensure_screen_awake():
    """Desactiva protector de pantalla y reposo tanto en consola como en entorno gráfico."""
    if shutil.which("setterm"):
        try:
            subprocess.run(["setterm", "-blank", "0", "-powerdown", "0"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    if os.environ.get("DISPLAY") and shutil.which("xset"):
        try:
            subprocess.run(["xset", "s", "off", "-dpms"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    # Si hay xsetroot, poner fondo negro puro
    if os.environ.get("DISPLAY") and shutil.which("xsetroot"):
        try:
            subprocess.run(["xsetroot", "-solid", "black", "-cursor_name", "left_ptr"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


def is_mounted(path_or_dev: str) -> bool:
    """Verifica si una partición o punto de montaje está montado en /proc/mounts."""
    try:
        with open("/proc/mounts", "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2 and (parts[0] == path_or_dev or parts[1] == path_or_dev):
                    return True
    except Exception:
        pass
    return False


def decode_mount_path(path: str) -> str:
    """Decodifica secuencias de escape octales en rutas de /proc/mounts (ej. \\040 -> espacio)."""
    try:
        return codecs.decode(path, "unicode_escape")
    except Exception:
        return path.replace(r"\040", " ").replace(r"\011", "\t")


def get_usb_partitions() -> List[str]:
    """Detecta particiones y discos de pendrives USB conectados."""
    partitions = []

    # 1. Por udev by-id (/dev/disk/by-id/usb-*)
    try:
        for p in sorted(glob.glob("/dev/disk/by-id/usb*")):
            if not p.endswith("-part"):
                real = os.path.realpath(p)
                if real.startswith("/dev/sd") and real not in partitions:
                    partitions.append(real)
    except Exception:
        pass

    # 2. Por /sys/class/block (particiones sda1, sdb1, etc.)
    try:
        part_devs = sorted(glob.glob("/sys/class/block/sd[a-z][1-9]*"))
        for p in part_devs:
            dev_path = f"/dev/{os.path.basename(p)}"
            if dev_path not in partitions:
                partitions.append(dev_path)

        # Si no hay particiones numeradas, buscar discos enteros (sda, sdb)
        if not partitions:
            disk_devs = sorted(glob.glob("/sys/class/block/sd[a-z]"))
            for d in disk_devs:
                dev_path = f"/dev/{os.path.basename(d)}"
                if dev_path not in partitions:
                    partitions.append(dev_path)
    except Exception as e:
        log(f"Error detectando particiones USB: {e}")

    # Priorizar particiones numeradas sobre discos enteros
    numbered = [p for p in partitions if any(c.isdigit() for c in p)]
    return numbered if numbered else partitions


def get_active_usb_mounts() -> List[str]:
    """Obtiene directorios de pendrives montados por el sistema (/media, /mnt, /run/media)."""
    mount_dirs = []
    base_dirs = ["/media", "/mnt", "/run/media"]
    ignore_exact = {"/", "/media", "/mnt", "/run/media", USB_MOUNT_POINT}

    try:
        with open("/proc/mounts", "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    dev, raw_mount = parts[0], parts[1]
                    mount_point = decode_mount_path(raw_mount)
                    if dev.startswith("/dev/sd") or any(mount_point.startswith(b) for b in base_dirs):
                        if os.path.isdir(mount_point) and mount_point not in ignore_exact:
                            mount_dirs.append(mount_point)
    except Exception as e:
        log(f"Error leyendo /proc/mounts: {e}")

    if is_mounted(USB_MOUNT_POINT) and os.path.isdir(USB_MOUNT_POINT):
        mount_dirs.append(USB_MOUNT_POINT)

    return list(dict.fromkeys(mount_dirs))


def auto_mount_first_pendrive() -> Optional[str]:
    """Si hay un pendrive conectado pero sin montar, lo monta en modo solo-lectura."""
    parts = get_usb_partitions()
    if not parts:
        return None

    # Si ya está montado en algún directorio por el sistema, usar ese
    active_mounts = get_active_usb_mounts()
    if active_mounts:
        return active_mounts[0]

    os.makedirs(USB_MOUNT_POINT, exist_ok=True)

    for dev in parts:
        if is_mounted(dev) or is_mounted(USB_MOUNT_POINT):
            continue

        log(f"Montando pendrive ({dev}) en modo seguro (solo-lectura)...")
        # 1. Intento de montaje genérico de Linux (sin la opción errónea 'nofail')
        r = subprocess.run(
            ["mount", "-o", "ro,noatime", dev, USB_MOUNT_POINT],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True
        )
        if r.returncode == 0:
            log(f"Pendrive montado con éxito en {USB_MOUNT_POINT}")
            return USB_MOUNT_POINT

        # 2. Intento con sistemas de archivos explícitos (vfat, exfat, ntfs-3g, ext4)
        for fs in ["vfat", "exfat", "ntfs-3g", "ntfs", "ext4"]:
            r2 = subprocess.run(
                ["mount", "-t", fs, "-o", "ro,noatime", dev, USB_MOUNT_POINT],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True
            )
            if r2.returncode == 0:
                log(f"Pendrive montado ({fs}) con éxito en {USB_MOUNT_POINT}")
                return USB_MOUNT_POINT

        err_msg = r.stderr.strip() if r.stderr else "desconocido"
        log(f"No se pudo montar {dev} de forma automática ({err_msg}).")

    return None


def unmount_pendrive():
    """Desmonta el pendrive del punto de montaje del kiosk."""
    if is_mounted(USB_MOUNT_POINT):
        try:
            subprocess.run(["umount", "-l", USB_MOUNT_POINT], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


def find_first_video(directory: str) -> Optional[str]:
    """
    Busca estrictamente el PRIMER video válido en el pendrive.
    Ignora archivos ocultos, archivos de sistema y metadatos de macOS (._*).
    """
    if not os.path.isdir(directory):
        return None

    candidates = []
    try:
        for root, dirs, files in os.walk(directory):
            # Excluir carpetas ocultas y de papelera
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".")
                and d.lower() not in ("system volume information", "$recycle.bin", ".trashes", "trashes", "found.000")
            ]
            for file in files:
                # Filtrar archivos ocultos y metadatos AppleDouble (._video.mp4)
                if file.startswith(".") or file.startswith("._"):
                    continue
                ext = os.path.splitext(file)[1].lower()
                if ext in VIDEO_EXTENSIONS:
                    full_path = os.path.join(root, file)
                    try:
                        # Descartar archivos vacíos o stubs corruptos (< 64 KB)
                        if os.path.getsize(full_path) > 64 * 1024:
                            candidates.append(full_path)
                    except OSError:
                        pass
    except Exception as e:
        log(f"Error explorando {directory}: {e}")

    if candidates:
        candidates.sort()
        return candidates[0]  # Modo estricto mono-archivo: el primero alfabéticamente

    return None


def build_mpv_command(video_path: str) -> List[str]:
    """
    Construye la línea de ejecución de MPV con aceleración por hardware en Pi 3.
    """
    return [
        "mpv",
        "--fullscreen",
        # Bucle infinito perfecto sin saltos ni pantalla negra
        "--loop-file=inf",
        "--keep-open=yes",
        # Aceleración de hardware H.264 V4L2 M2M con fallback seguro
        "--hwdec=auto-safe",
        # Prioridad de salida de video: GPU con fallback automático a DRM para consola pura
        "--vo=gpu,drm",
        "--profile=fast",
        "--vd-lavc-threads=4",
        # Caché generoso en RAM para evitar micro-tirones al leer de USB
        "--demuxer-max-bytes=32M",
        "--demuxer-readahead-secs=10",
        # Audio automático por HDMI al 100%
        "--audio-device=auto",
        "--audio-channels=auto-safe",
        "--volume=100",
        # Interfaz 100% limpia sin menús, cursor ni texto en pantalla
        "--cursor-autohide=always",
        "--no-terminal",
        "--no-osd-bar",
        "--osd-level=0",
        video_path
    ]


class Pi3KioskPlayer:
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.current_video_file: Optional[str] = None
        self.running = True

    def stop_playback(self):
        """Detiene MPV y limpia el proceso."""
        if self.process:
            log("Deteniendo reproductor...")
            try:
                self.process.terminate()
                self.process.wait(timeout=1.5)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None
        self.current_video_file = None

    def start_playback(self, video_file: str) -> bool:
        """Inicia la reproducción del video seleccionado."""
        self.stop_playback()
        if not video_file or not os.path.exists(video_file):
            return False

        setup_display_environment()
        ensure_screen_awake()
        cmd = build_mpv_command(video_file)

        log(f"▶ Reproduciendo video único: {os.path.basename(video_file)}")
        log(f"  Ruta: {video_file}")

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True
            )
            self.current_video_file = video_file

            # Comprobar si arranca o si falla en el primer segundo
            time.sleep(0.5)
            if self.process.poll() is not None:
                err = self.process.stderr.read() if self.process.stderr else ""
                log(f"⚠️ MPV falló al iniciar (código {self.process.returncode}): {err.strip()}")
                self.process = None
                self.current_video_file = None
                return False

            log("🎬 Video iniciado y reproduciendo en bucle continuo.")
            return True
        except Exception as e:
            log(f"Error al ejecutar MPV: {e}")
            self.process = None
            self.current_video_file = None
            return False

    def scan_usb_for_video(self) -> Optional[str]:
        """Detecta pendrive USB y retorna el primer video encontrado."""
        auto_mount_first_pendrive()
        mounts = get_active_usb_mounts()

        for m in mounts:
            vid = find_first_video(m)
            if vid:
                return vid

        return None

    def run(self):
        """Ciclo principal continuo: vigila presencia del pendrive e inicia/detiene el video."""
        log("================================================================")
        log("🚀 Pi 3 Video Kiosk Activado (Esperando Pendrive USB)")
        log("================================================================")
        ensure_screen_awake()

        while self.running:
            try:
                video = self.scan_usb_for_video()

                if video:
                    # Caso A: Se detectó un video en el pendrive
                    if video != self.current_video_file:
                        log("Detectado nuevo video en pendrive USB. Iniciando...")
                        self.start_playback(video)
                    else:
                        # Si el reproductor se cerró por alguna razón, relanzarlo de inmediato
                        if self.process is None or self.process.poll() is not None:
                            log("El proceso de video se cerró. Relanzando bucle...")
                            self.start_playback(video)
                else:
                    # Caso B: No hay pendrive conectado o no tiene videos
                    if self.process is not None:
                        log("Pendrive desconectado. Deteniendo video y dejando pantalla en negro...")
                        self.stop_playback()
                        unmount_pendrive()

                time.sleep(2.0)

            except KeyboardInterrupt:
                break
            except Exception as e:
                log(f"Aviso en ciclo de monitoreo: {e}")
                time.sleep(2.0)

        self.stop_playback()
        unmount_pendrive()
        log("Pi 3 Kiosk detenido.")


def main():
    if not shutil.which("mpv"):
        log("ADVERTENCIA: 'mpv' no está instalado. Ejecutá: sudo apt install -y mpv")

    player = Pi3KioskPlayer()

    def handle_exit(sig, frame):
        player.running = False
        player.stop_playback()
        unmount_pendrive()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    player.run()


if __name__ == "__main__":
    main()

