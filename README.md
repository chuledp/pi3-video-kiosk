# 🎬 Pi 3 Video Kiosk (Modo Kiosk Headless Pendrive)

Sistema ultra-optimizado, ultra-simple y sin dependencias para **Raspberry Pi 3**:
* **Modo Kiosk Headless Puro**: Sin escritorio, sin ventanas, sin cursor, sin menús ni texto en pantalla.
* **Plug & Play con Pendrive USB**: Conectás cualquier pendrive y arranca a reproducir de inmediato.
* **Estricto Mono-Archivo**: Si hay varios videos, toma únicamente el primero e ignora el resto.
* **Pantalla en Negro en Reposo**: Si no hay pendrive (o se desconecta en caliente), la pantalla queda en negro esperando en silencio sin errores.
* **1080p H.264 por Hardware**: Configurado con `v4l2m2m` + multihilo en la GPU VideoCore IV para reproducción a 60 fps sin tirones.
* **Bucle Infinito Continuo**: Repetición fluida sin parpadeos ni pantalla negra entre loops.
* **Audio por HDMI al 100%**: Sonido directo a televisores o proyectores.
* **Filtro Anti-Mac**: Ignora automáticamente archivos basura de macOS (`._video.mp4` y `.Trashes`).

---

## 🚀 Instalación en la Raspberry Pi 3

Dentro de la carpeta `pi3-video-kiosk/`, ejecutá:

```bash
sudo ./install.sh
```

El script se encarga automáticamente de:
1. Instalar `mpv` y las utilidades de audio.
2. Configurar la memoria GPU a 128 MB en `/boot/config.txt` (indispensable para 1080p en Pi 3).
3. Desactivar el protector de pantalla y el apagado de pantalla en consola.
4. Crear y activar el servicio `systemd` para arranque automático en cada encendido.

---

## 💾 Cómo preparar el Pendrive

1. Formateá el pendrive en **FAT32** o **exFAT**.
2. Copiá tu video en formato **1080p H.264** (`.mp4`, `.mov`, `.mkv`).
3. Enchufalo a la Raspberry Pi 3.
4. **¡Listo!** El sistema lo monta solo en modo seguro de solo-lectura (protegiendo el pendrive si alguien desconecta la energía de golpe) y arranca a reproducir a pantalla completa.

---

## 🛠️ Comandos útiles

* **Ver el log en vivo:**
  ```bash
  sudo journalctl -u pi3-video-kiosk -f
  ```
* **Reiniciar el servicio:**
  ```bash
  sudo systemctl restart pi3-video-kiosk
  ```
* **Detener el servicio:**
  ```bash
  sudo systemctl stop pi3-video-kiosk
  ```
* **Desinstalar:**
  ```bash
  sudo /opt/pi3-video-kiosk/uninstall.sh
  ```

