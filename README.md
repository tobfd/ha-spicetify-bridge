<img src="https://raw.githubusercontent.com/tobfd/ha-spicetify-bridge/master/custom_components/spicetify_bridge/brand/logo.png" alt="Spicetify Bridge Logo" height="200"/>

[![HACS Badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge&color=039be5)](https://github.com/hacs/default)
[![GitHub Release](https://img.shields.io/github/v/release/tobfd/ha-spicetify-bridge?style=for-the-badge&logo=github&color=039be5)](https://github.com/tobfd/ha-spicetify-bridge/releases/latest)
[![GitHub License](https://img.shields.io/github/license/tobfd/ha-spicetify-bridge?style=for-the-badge&color=039be5&logo=github)](https://github.com/tobfd/ha-spicetify-bridge/blob/main/LICENSE)
[![Home Assistant Minimum Version](https://img.shields.io/badge/Home%20Assistant-2026.3.0%2B-blue?style=for-the-badge&logo=homeassistant&logoColor=white&color=039be5)](https://www.home-assistant.io/)

A feature-rich Home Assistant custom component that provides local push-based real-time control over your **Spotify Desktop Client** via [Spicetify](https://spicetify.app/) and the [spicetify-connect-api](https://github.com/tobfd/spicetify-connect-api) extension.

Powered by the [spicetify-websocket](https://github.com/tobfd/spicetify-websocket) Python library.

---

## ✨ Features

- ⚡ **Local Push Architecture**: Instantaneous, millisecond-accurate state updates without network polling.
- 🎵 **Full Media Player Controls**: Play, pause, skip, timeline seek, volume control, mute, shuffle, repeat modes, and direct Spotify URI/URL playback.
- 💚 **Track Favoriting / Hearts**: Native Home Assistant favorite support.
- 🔒 **Secure WebSockets (WSS)**: Built-in support for encrypted WSS connections using self-signed or trusted SSL certificates.
- 🔑 **API Key Authentication**: Protect incoming commands and outgoing events with token authentication.

---

## 📋 Prerequisites

To use this integration, you need:

1. **Spotify Desktop Client** installed on your PC or server.
2. **[Spicetify CLI](https://spicetify.app/)** installed.
3. The **[spicetify-connect-api](https://github.com/tobfd/spicetify-connect-api)** extension (`v0.3.0` or higher) enabled in Spicetify.

---

## 📥 Installation

### Method 1: HACS (Recommended)

1. Open **HACS** in your Home Assistant sidebar.
2. Click the **three dots** in the top right corner and select **Custom repositories**.
3. Add `https://github.com/tobfd/ha-spicetify-bridge` with category **Integration**.
4. Search for **Spicetify Bridge** and click **Download**.
5. **Restart Home Assistant**.

### Method 2: Manual Installation

1. Download the `custom_components/spicetify_bridge` folder from the latest release.
2. Copy the `spicetify_bridge` folder into your Home Assistant `<config_dir>/custom_components/` directory.
3. **Restart Home Assistant**.

---

## ⚙️ Configuration

1. In Home Assistant, go to **Settings → Devices & Services → Add Integration**.
2. Search for **Spicetify Bridge**.
3. Configure the connection parameters:
   - **Host**: `0.0.0.0` (binds to all network interfaces, recommended).
   - **Port**: `9090` (default).
   - **API Key**: *(Optional)* Secret token matching your Spicetify extension configuration.
   - **Enable WSS / SSL**: Check this box if Home Assistant and Spotify run on different computers.

<details>
<summary><b>🔒 WSS / SSL & Certificate Setup Guide (Click to Expand)</b></summary>

<br/>

> **Why is WSS / SSL required?**
> Spotify Desktop is built on Chromium and enforces strict security policies. If Home Assistant and Spotify run on **different devices** on your local network, Spotify blocks unencrypted (`ws://`) WebSocket connections. You **must** enable WSS (`wss://`) and use an SSL certificate.

### Step 1: Generate Certificate Files (`cert.pem` & `key.pem`)

Choose **one** of the following methods to generate your certificates:

#### Option A: Using OpenSSL (Linux / WSL / macOS)
Replace `192.168.178.200` with the **IP address of your Home Assistant server**:
```bash
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 3650 -nodes -subj "/CN=192.168.178.200" -addext "subjectAltName=IP:192.168.178.200"
```
*Note: Run `Import-Certificate -FilePath "C:\path\to\cert.pem" -CertStoreLocation Cert:\LocalMachine\Root` in Admin PowerShell on Windows to trust this certificate.*

#### Option B: Windows 11 using `mkcert` (Automatic Trust)
1. Install `mkcert` via PowerShell (Administrator):
   ```powershell
   choco install mkcert   # or 'scoop install mkcert'
   ```
2. Install the local Root CA into Windows:
   ```powershell
   mkcert -install
   ```
3. Generate the certificates for your Home Assistant IP:
   ```powershell
   mkcert -cert-file cert.pem -key-file key.pem 192.168.178.200 # Replace with your Home Assistant IP
   ```

---

### Step 2: Upload Certificates to Home Assistant
1. Install the **Advanced SSH & Web Terminal** App in Home Assistant (**Settings → App**).
2. Set `username` to `root`, enable **SFTP**, set a password, and start the add-on.
3. Connect via SFTP (e.g. Termius, WinSCP, or FileZilla) and upload `cert.pem` and `key.pem` into the `/ssl/` directory.

---

### Step 3: Configure Spicetify Extension
1. Open **Spotify Desktop**.
2. Click your **profile picture** → **Connect API Settings**.
3. Set the Server URL:
   - For WSS: `wss://YOUR_HOME_ASSISTANT_IP:9090` # Probably this one if Home Assistant and Spotify are on different devices.
   - For local unencrypted WS: `ws://127.0.0.1:9090`
4. Enter your API Key if configured.
5. **Restart Spotify completely**.

</details>

## ▶️ Usage & Media Playback

Spicetify Bridge integrates as a standard Home Assistant `media_player` entity. It supports all standard media controls: play, pause, stop, next/previous track, volume adjustment, mute, timeline seeking, shuffle, repeat modes, and native track favoriting.

### 🎵 Playing Media (`media_player.play_media`)

You can start playing any Spotify track, album, or playlist by calling the `media_player.play_media` action in your Home Assistant automations, dashboards, or Developer Tools.

| Playback Type       | `media_content_type`             | `media_content_id` Example                              |
|:--------------------|:---------------------------------|:--------------------------------------------------------|
| **Track URI**       | `music` or `spotify:track`       | `spotify:track:55pBIZO1cqoldeqpp5WR7H?`                 |
| **Album URI**       | `album` or `spotify:album`       | `spotify:album:7aJuG4TFXa2hmE4z1yxc3n`                  |
| **Playlist URI**    | `playlist` or `spotify:playlist` | `spotify:playlist:37i9dQZF1DXcBWIGoYBM5M`               |
| **Spotify Web URL** | `music`                          | `https://open.spotify.com/track/55pBIZO1cqoldeqpp5WR7H` |

---

## 🧩 Provided Entities

| Entity Type    | Unique Key          | Default Entity Name               | Description                                                                           |
|:---------------|:--------------------|:----------------------------------|:--------------------------------------------------------------------------------------|
| `media_player` | `media_player`      | `Spicetify Desktop Client (9090)` | Primary playback control entity with native favorite support and dynamic permissions. |
| `switch`       | `liked_track`       | `Liked track`                     | Switch to view and toggle the heart/liked status of the current song.                 |
| `button`       | `force_previous`    | `Force previous track`            | Skip to the previous track regardless of elapsed playback time.                       |
| `button`       | `ping_client`       | `Ping client`                     | Trigger a manual latency check.                                                       |
| `sensor`       | `connection_status` | `Connection status`               | WebSocket connection state (`Connected` / `Disconnected`).                            |
| `sensor`       | `ping_latency`      | `Ping latency`                    | Round-trip WebSocket latency in milliseconds (`ms`). Disabled by default (diagnostic). |
