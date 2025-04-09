# 🧠 Rustalytics – Rust+ Real-Time Monitoring Bot

Rustalytics is a real-time monitoring bot for Rust servers using the official Rust+ companion system.  
It keeps your team updated automatically with in-game alerts for:

- 🚁 Patrol Helicopters  
- 🚢 Cargo Ship spawns  
- 💥 Explosions  (Not Displayable on Rust + | Not Working)
- 🎯 CH47 drops and Oil Rig detection  
- 🧍 Online/offline, AFK status, and deaths  
- ⏰ Server time, sunrise/sunset info  
- 💬 Team chat commands  

> Built for 24/7 deployment so you never miss a moment.

---

## 🛠 Features

- Tracks major world events and player activity
- Posts alerts directly in Rust+ team chat
- Detects CH47s landing at Oil Rigs
- Oil Rig 15-minute engagement timer
- AFK detection and online/offline status
- Fully automated with no manual intervention
- Designed for free cloud deployment (Railway/Render)

---

## 🚀 Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/PeterTech-Dev/Rustalytics.git
cd Rustalytics
```

### 2. Install the required dependencies

```bash
pip install -r requirements.txt
```

### 3. Add `config.json` and `server.json`

These two files are required to link to your Rust+ account and server.

To generate them easily:

👉 **Install the [RustPlus.py Link Companion Chrome Extension](https://chrome.google.com/webstore/detail/rustpluspy-link-companion/gojhnmnggbnflhdcpcemeahejhcimnlf?hl=en)**

Once you open Rust+ and link a server, this extension will automatically generate the files:

- `server.json` – contains your server IP, port, Steam ID, and token.
- `config.json` – contains your Expo push token, FCM credentials, and Rust+ auth token.

📝 Copy both of these files into the **root** of your Rustalytics folder.

To keep your **sensitive values private** when deploying to platforms like GitHub, Railway, or Render, create a `.env` file like this:

```env
# From config.json
EXPO_PUSH_TOKEN=...
FCM_TOKEN=...
GCM_ANDROID_ID=...
GCM_SECURITY_TOKEN=...
RUSTPLUS_AUTH_TOKEN=...

# From server.json
SERVER_IP=129.232.149.98
SERVER_PORT=27141
PLAYER_ID=76561198884329745
PLAYER_TOKEN=-528216812
```

### 4. Add Public API keys to Python

### 🧪 Rust+ API Setup

These values are used to communicate with the **official Rust+ push servers**.  
They do **not change** and are publicly available:

```env
API_KEY=AIzaSyB5y2y-Tzqb4-I4Qnlsh_9naYv_TD8pCvY
PROJECT_ID=rust-companion-app
GCM_SENDER_ID=976529667804
GMS_APP_ID=1:976529667804:android:d6f1ddeb4403b338fea619
ANDROID_PACKAGE_NAME=com.facepunch.rust.companion
ANDROID_PACKAGE_CERT=E28D05345FB78A7A1A63D70F4A302DBF426CA5AD
```

If you ever need to reference them again, they’re also shared in the 📣 [Rust+ API Discord](https://discord.gg/uj8nkK4qJr).

---

## 💬 Available Commands

Once deployed, use these in Rust+ team chat:

```plaintext
.help       → Show command list
.heli       → Time since last Patrol Heli
.bradley    → Time until Bradley respawn
.cargo      → Time since last Cargo Ship
.time       → Current server time & next sunrise/sunset
.team       → Online and AFK teammates
.offline    → Offline durations (if tracked)
.leader     → Promote the message sender to team leader
```

---

## 🙏 Special Thanks

This project wouldn't be possible without:

🧠 [`rustplus`](https://github.com/olijeffers0n/rustplus)  
By [**olijeffers0n**](https://github.com/olijeffers0n)

👏 Big thanks to the Rust+ community for unlocking this awesome functionality!

---

## 📜 License

This project is licensed under the **MIT License**.  
You're free to use, fork, and build on top of it!

---

## 🔗 Links

- GitHub: [github.com/PeterTech-Dev/Rustalytics](https://github.com/PeterTech-Dev/Rustalytics)
- RustPlus.py Library: [github.com/olijeffers0n/rustplus](https://github.com/olijeffers0n/rustplus)
- Chrome Extension (RustPlus.py Link):  
  [Install from Chrome Webstore](https://chrome.google.com/webstore/detail/rustpluspy-link-companion/gojhnmnggbnflhdcpcemeahejhcimnlf?hl=en)

---

## 👨‍💻 Author

Built with ❤️ by [PeterTech-Dev](https://github.com/PeterTech-Dev)  
Want to contribute? PRs and stars are always welcome ⭐
