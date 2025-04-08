import json
import os
import sys
import threading
import webbrowser
from queue import Queue
from uuid import uuid4

import requests
import urllib3
from flask import Flask, render_template, request
from push_receiver import PushReceiver
from push_receiver.android_fcm_register import AndroidFCM
from rustplus import RustSocket, ServerDetails, RustError
from rustplus.exceptions import RequestError
import asyncio
import time

from dotenv import load_dotenv
load_dotenv()


API_KEY = os.getenv("API_KEY")
PROJECT_ID = os.getenv("PROJECT_ID")
GCM_SENDER_ID = os.getenv("GCM_SENDER_ID")
GMS_APP_ID = os.getenv("GMS_APP_ID")
ANDROID_PACKAGE_NAME = os.getenv("ANDROID_PACKAGE_NAME")
ANDROID_PACKAGE_CERT = os.getenv("ANDROID_PACKAGE_CERT")
fcm_token = os.getenv("fcm_token")

def convert_coordinates(pos, map_size):
    grid_size = 146.28571428571428
    converted_size = int(map_size / grid_size)
    grid_letter_index = int(pos[0] / grid_size)
    grid_number = int((converted_size - pos[1] / grid_size))

    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    grid_letter = ""
    while grid_letter_index >= 0:
        grid_letter = alphabet[grid_letter_index % 26] + grid_letter
        grid_letter_index = (grid_letter_index // 26) - 1

    return f"{grid_letter}{grid_number + 7}"


class RustPlusCLI:
    def __init__(self):
        self.chrome_path = self.detect_chrome()
        self.last_heli_spawn_time = None
        self.last_bradley_kill_time = None
        self.last_cargo_id = None
        self.last_cargo_spawn_time = None
        self.oilrig_timer_end = None
        self.team_status = {}
        self.offline_tracker = {}
        self.afk_tracker = {}
        self.chat_history = set()
        self.dead_players = set()
        self.afk_announced = set()

    def detect_chrome(self):
        if sys.platform.startswith("win"):
            return "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
        elif sys.platform.startswith("darwin"):
            return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        else:
            return "/usr/bin/google-chrome"

    def load_socket(self):
        ip = os.getenv("ip")
        player_token = os.getenv("playerToken")
        port = os.getenv("port")
        steam_id=os.getenv("playerId")

        if not all([ip, port, steam_id, player_token]):
            print("❌ Missing server details in .env")
            return None

        details = ServerDetails(ip, port, steam_id, player_token)
        return RustSocket(details)

def format_time(seconds):
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m" if hours else f"{minutes}m {seconds}s"


async def monitor_map_events():
    cli = RustPlusCLI()
    socket = cli.load_socket()
    if not socket:
        return
    await socket.connect()
    map_info = await socket.get_map_info()
    map_size = map_info.width
    oilrig_names = ["large oil rig", "small oil rig"]
    oilrig_locations = [m for m in map_info.monuments if m.token.lower() in oilrig_names]
    print("\n👁️ Monitoring map events. Press Ctrl+C to stop.")

    seen_explosions = set()
    seen_ch47_ids = set()
    heli_announced = False
    cargo_announced = False
    last_info_time = time.time()

    while True:
        try:
            now = time.time()
            if now - last_info_time >= 900:
                info = await socket.get_info()
                await socket.send_team_message(f"👥 Server: {info.players}/{info.max_players} players, Queued: {info.queued_players}")
                last_info_time = now

            chat_msgs = await socket.get_team_chat()
            for msg in chat_msgs:
                if msg.time in cli.chat_history:
                    continue
                cli.chat_history.add(msg.time)
                text = msg.message.lower().strip()

                if text.startswith(".heli") and cli.last_heli_spawn_time:
                    diff = time.time() - cli.last_heli_spawn_time
                    await socket.send_team_message(f":lmg.m249: Last Patrol Heli: {format_time(diff)} ago")

                elif text.startswith(".bradley") and cli.last_bradley_kill_time:
                    respawn = 3600 - (time.time() - cli.last_bradley_kill_time)
                    if respawn > 0:
                        await socket.send_team_message(f":lmg.m249: Bradley respawn in: {format_time(respawn)}")
                    else:
                        await socket.send_team_message(":lmg.m249: Bradley is ready to spawn!")

                elif text.startswith(".team"):
                    try:
                        info = await socket.get_team_info()
                        if not info or not hasattr(info, "members"):
                            raise ValueError("Invalid team info received.")
                    except Exception:
                        await socket.send_team_message("⚠️ Could not get team info. Possibly rate limited.")
                        continue

                    online, afk = [], []
                    for m in info.members:
                        if m.is_online:
                            if m.steam_id in cli.afk_tracker and time.time() - cli.afk_tracker[m.steam_id]["last_move"] >= 300:
                                afk.append(m.name)
                            else:
                                online.append(m.name)
                    await socket.send_team_message(f":coffeecan: Online: {', '.join(online)} | AFK: {', '.join(afk)}")

                elif text.startswith(".cargo") and cli.last_cargo_spawn_time:
                    diff = time.time() - cli.last_cargo_spawn_time
                    await socket.send_team_message(f":water.radioactive: Last Cargo: {format_time(diff)} ago")

                elif text.startswith(".time"):
                    server_time = await socket.get_time()
                    if isinstance(server_time, RustError):
                        await socket.send_team_message("❌ Could not retrieve server time.")
                    else:
                        try:
                            # Convert time strings to total seconds
                            now_sec = sum(int(x) * 60 ** i for i, x in enumerate(reversed(server_time.time.split(":"))))
                            sunrise_sec = sum(int(x) * 60 ** i for i, x in enumerate(reversed(server_time.sunrise.split(":"))))
                            sunset_sec = sum(int(x) * 60 ** i for i, x in enumerate(reversed(server_time.sunset.split(":"))))

                            # Determine the next event
                            if now_sec < sunrise_sec:
                                next_event = f"Sunrise at {server_time.sunrise}"
                            elif now_sec < sunset_sec:
                                next_event = f"Sunset at {server_time.sunset}"
                            else:
                                next_event = f"Sunrise at {server_time.sunrise}"  # next sunrise is tomorrow

                            await socket.send_team_message(f"🕓 Server Time: {server_time.time} | Next: {next_event}")
                        except Exception:
                            await socket.send_team_message(f"🕓 Server Time: {server_time.time}")


                elif text.startswith(".offline"):
                    info = await socket.get_team_info()
                    offline = [f"{m.name}: {int((time.time() - cli.offline_tracker[m.steam_id]) // 60)}m"
                               for m in info.members if not m.is_online and m.steam_id in cli.offline_tracker]
                    await socket.send_team_message("Offline: " + " | ".join(offline) if offline else "No offline members tracked.")

                elif text.startswith(".leader"):
                    try:
                        await socket.promote_to_team_leader(msg.steam_id)
                        await socket.send_team_message(f"👑 {msg.name} is now the team leader!")
                    except RequestError:
                        await socket.send_team_message(":worried: I'm not leader sorry")

                elif text.startswith(".help"):
                    commands = [
                        ".heli", ".bradley", ".team", ".cargo", ".time", ".offline", ".leader", ".help"
                    ]
                    await socket.send_team_message(f"Commands: {', '.join(commands)}")

            markers = await socket.get_markers()
            patrols = [m for m in markers if m.type == 8]
            explosions = [m for m in markers if m.type == 2]
            ch47s = [m for m in markers if m.type == 4]
            cargos = [m for m in markers if m.type == 5]

            if patrols and not heli_announced:
                heli = patrols[0]
                grid = convert_coordinates((heli.x, heli.y), map_size)
                cli.last_heli_spawn_time = time.time()
                await socket.send_team_message(f":lmg.m249: Patrol Helicopter is out at {grid}")
                heli_announced = True
            elif not patrols:
                heli_announced = False

            for ch in ch47s:
                if ch.id not in seen_ch47_ids:
                    seen_ch47_ids.add(ch.id)
                    ch_grid = convert_coordinates((ch.x, ch.y), map_size)
                    near_oilrig = any(((ch.x - rig.x)**2 + (ch.y - rig.y)**2) ** 0.5 < 0.03 for rig in oilrig_locations)
                    msg = f":scientist: CH47 landed at Oil Rig — someone is doing oil! ({ch_grid})" if near_oilrig else f":scientist: CH47 dropping crate at {ch_grid}"
                    cli.oilrig_timer_end = time.time() + 900 if near_oilrig else cli.oilrig_timer_end
                    await socket.send_team_message(msg)

            if cargos and (not cli.last_cargo_id or cargos[0].id != cli.last_cargo_id):
                c = cargos[0]
                grid = convert_coordinates((c.x, c.y), map_size)
                cli.last_cargo_id = c.id
                cli.last_cargo_spawn_time = time.time()
                await socket.send_team_message(f" :water.radioactive: Cargo Ship is sailing at {grid}")

            for explosion in explosions:
                if explosion.id not in seen_explosions:
                    seen_explosions.add(explosion.id)
                    grid = convert_coordinates((explosion.x, explosion.y), map_size)
                    await socket.send_team_message(f":exclamation: Explosion detected at {grid}")

            try:
                team_info = await socket.get_team_info()
            except RequestError:
                await socket.send_team_message(":warning: Can't fetch team info — not leader.")
                await asyncio.sleep(10)
                continue
            for member in team_info.members:
                sid = member.steam_id
                name = member.name
                if sid not in cli.team_status:
                    cli.team_status[sid] = member.is_online
                    if not member.is_online:
                        cli.offline_tracker[sid] = time.time()
                    continue

                if cli.team_status[sid] != member.is_online:
                    cli.team_status[sid] = member.is_online
                    if member.is_online:
                        await socket.send_team_message(f"{name} is now  :wave: ONLINE :heart:")
                    else:
                        cli.offline_tracker[sid] = time.time()
                        await socket.send_team_message(f"{name} is now  :wave: OFFLINE X")

                if member.is_online:
                    prev = cli.afk_tracker.get(sid, {"x": member.x, "y": member.y, "last_move": time.time()})
                    moved = abs(prev["x"] - member.x) > 0.001 or abs(prev["y"] - member.y) > 0.001
                    if moved:
                        cli.afk_tracker[sid] = {"x": member.x, "y": member.y, "last_move": time.time()}
                        cli.afk_announced.discard(sid)
                    elif time.time() - prev["last_move"] >= 300 and sid not in cli.afk_announced:
                        await socket.send_team_message(f":eyes: {name} appears to be AFK.")
                        cli.afk_announced.add(sid)

                if not member.is_alive and sid not in cli.dead_players:
                    grid = convert_coordinates((member.x, member.y), map_size)
                    await socket.send_team_message(f":skull: {name} died at {grid}")
                    cli.dead_players.add(sid)
                elif member.is_alive:
                    cli.dead_players.discard(sid)

            if cli.oilrig_timer_end and time.time() >= cli.oilrig_timer_end:
                await socket.send_team_message("Oil Rig timer ended — stay alert!")
                cli.oilrig_timer_end = None

            await asyncio.sleep(10)

        except Exception as e:
            print(f"Unexpected error: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(monitor_map_events())
