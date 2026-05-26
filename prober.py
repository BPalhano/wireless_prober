

#!/usr/bin/env python3
"""
Bluetooth and Wi-Fi scanner V2.0 .
Run with: sudo python3 prober.py

Assure you have the follow packages installed:

- bluez (for hcitool, hciconfig, sdptool)
- wireless-tools (for iwlist)
- bleak (for BLE scanning): pip3 install bleak
- iw (for Wi-Fi interface detection): sudo apt install iw

This script performs:
1. Bluetooth Classic scanning using hcitool and hciconfig.
2. Bluetooth LE scanning using Bleak.
3. Wi-Fi scanning using iwlist.

Author: Igor Braga Palhano
"""

import asyncio
import subprocess
import sys
import os
import shutil
from datetime import datetime

# Root check
def check_root():
    if os.geteuid() != 0:
        print("Run as root: sudo python3 prober.py")
        sys.exit(1)

# Bluetooth Classic via hcitool + hciconfig (without PyBluez)
def scan_bluetooth_classic_hci():
    print("\n" + "="*60)
    print("BLUETOOTH CLASSIC - hcitool")
    print("="*60)

    # Check whether the adapter is active.
    try:
        hci_info = subprocess.run(
            ["hciconfig", "-a"],
            capture_output=True, text=True, timeout=5
        )
        print("Detected Bluetooth adapters:")
        print(hci_info.stdout if hci_info.stdout else "  No adapter found.")
    except FileNotFoundError:
        print("hciconfig not found. Install it with: sudo apt install bluez")
    except Exception as e:
        print(f"Error: {e}")

    # Scan devices.
    print("\nScanning for devices (8 seconds)...\n")
    try:
        result = subprocess.run(
            ["hcitool", "scan", "--flush"],
            capture_output=True, text=True, timeout=20
        )

        lines = result.stdout.strip().splitlines()

        if len(lines) <= 1:
            print("No Bluetooth Classic device found.")
            print("Hint: make sure devices are in discoverable mode.")
        else:
            devices = []
            for line in lines[1:]:
                parts = line.strip().split("\t")
                if len(parts) >= 2:
                    mac  = parts[0].strip()
                    name = parts[1].strip() if len(parts) > 1 else "Unknown"
                    devices.append((mac, name))

            print(f"Found {len(devices)} device(s):\n")

            for mac, name in devices:
                print(f"{'-'*50}")
                print(f"Name       : {name}")
                print(f"MAC Address: {mac}")

                # Detailed device information via hcitool info.
                try:
                    info = subprocess.run(
                        ["hcitool", "info", mac],
                        capture_output=True, text=True, timeout=10
                    )
                    if info.stdout:
                        print("Details:")
                        for l in info.stdout.strip().splitlines():
                            print(f"  {l}")
                except Exception:
                    pass

                # Inquiry details for nearby devices.
                try:
                    cls_result = subprocess.run(
                        ["hcitool", "inq", "--flush", "--length=1"],
                        capture_output=True, text=True, timeout=10
                    )
                    if cls_result.stdout:
                        print(f"Inquiry Info: {cls_result.stdout.strip()}")
                except Exception:
                    pass

                print()

    except subprocess.TimeoutExpired:
        print("Scan timed out.")
    except FileNotFoundError:
        print("hcitool not found. Install it with: sudo apt install bluez")
    except Exception as e:
        print(f"Error: {e}")


def scan_bluetooth_sdp(mac):
    """Look up public SDP services for a device."""
    print(f"\nLooking up SDP services for {mac}...")
    try:
        result = subprocess.run(
            ["sdptool", "browse", mac],
            capture_output=True, text=True, timeout=15
        )
        if result.stdout:
            for line in result.stdout.strip().splitlines():
                print(f"  {line}")
        else:
            print("  No public SDP service found.")
    except FileNotFoundError:
        print("  sdptool not found: sudo apt install bluez")
    except Exception as e:
        print(f"  SDP error: {e}")


# Bluetooth LE via Bleak
async def scan_bluetooth_le():
    print("\n" + "="*60)
    print("BLUETOOTH LOW ENERGY (BLE) - Bleak")
    print("="*60)

    try:
        from bleak import BleakScanner
        from bleak.backends.device import BLEDevice

        found_devices = {}

        def callback(device: BLEDevice, advertisement_data):
            if device.address not in found_devices:
                found_devices[device.address] = {
                    'device'           : device,
                    'advertisement'    : advertisement_data
                }

        print("Capturing BLE advertisements for 12 seconds...\n")

        scanner = BleakScanner(detection_callback=callback)
        await scanner.start()
        await asyncio.sleep(12)
        await scanner.stop()

        if not found_devices:
            print("No BLE device found.")
            return

        print(f"Found {len(found_devices)} BLE device(s):\n")

        for addr, data in found_devices.items():
            dev = data['device']
            adv = data['advertisement']
            rssi = getattr(adv, 'rssi', 'N/A') if adv is not None else 'N/A'

            print(f"{'-'*50}")
            print(f"Name            : {dev.name if dev.name else 'Unknown'}")
            print(f"MAC Address     : {dev.address}")
            print(f"RSSI            : {rssi} dBm")

            if adv:
                print(f"TX Power        : {adv.tx_power if adv.tx_power is not None else 'N/A'} dBm")

                if adv.local_name:
                    print(f"Local Name      : {adv.local_name}")

                if adv.manufacturer_data:
                    print("Manufacturer Data:")
                    for company_id, data_bytes in adv.manufacturer_data.items():
                        print(f"  ID 0x{company_id:04X}: {data_bytes.hex()}")

                if adv.service_uuids:
                    print("Service UUIDs   :")
                    for uuid in adv.service_uuids:
                        print(f"  - {uuid}")

                if adv.service_data:
                    print("Service Data    :")
                    for uuid, sdata in adv.service_data.items():
                        print(f"  {uuid}: {sdata.hex()}")

            print()

    except ImportError:
        print("Bleak is not installed.")
        print("Run: pip3 install bleak")
    except Exception as e:
        print(f"BLE error: {e}")
        error_text = str(e)
        if "ServiceUnknown" in error_text or "org.bluez" in error_text:
            print("Hint: BlueZ DBus service not found.")
            print("      Install/start Bluetooth service and verify org.bluez on system DBus.")
            print("      Example: sudo apt install bluez && sudo systemctl enable --now bluetooth")
            print("      Check with: gdbus introspect --system --dest org.bluez --object-path /")
        else:
            print("Hint: verify Bluetooth is active: sudo systemctl start bluetooth")


# Wi-Fi via iwlist + iw
def get_wifi_interface():
    """Detect the Wi-Fi interface automatically."""
    try:
        result = subprocess.run(["iw", "dev"], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if "Interface" in line:
                return line.strip().split()[-1]
    except Exception:
        pass

    for iface in ["wlan0", "wlan1", "wlp2s0", "wlp3s0", "wlp4s0"]:
        r = subprocess.run(["ip", "link", "show", iface],
                           capture_output=True, text=True)
        if r.returncode == 0:
            return iface
    return None


def parse_iwlist(output):
    """Parse the output of iwlist scan."""
    networks = []
    current  = {}

    for line in output.splitlines():
        line = line.strip()

        if line.startswith("Cell"):
            if current:
                networks.append(current)
            current = {}
            if "Address:" in line:
                current['bssid'] = line.split("Address:")[-1].strip()

        elif "ESSID:" in line:
            ssid = line.split("ESSID:")[-1].strip().strip('"')
            current['ssid'] = ssid if ssid else "<Hidden>"

        elif "Channel:" in line and 'channel' not in current:
            current['channel'] = line.split("Channel:")[-1].strip()

        elif "Frequency:" in line:
            current['frequency'] = line.split("Frequency:")[-1].strip()

        elif "Quality=" in line:
            for part in line.split():
                if "Quality=" in part:
                    current['quality'] = part.replace("Quality=", "")
                if "level=" in part:
                    current['signal'] = part.replace("Signal level=", "").replace("level=", "")

        elif "Encryption key:" in line:
            enc = line.split(":")[-1].strip()
            current['encryption'] = "Enabled" if enc == "on" else "Open"

        elif "Mode:" in line:
            current['mode'] = line.split("Mode:")[-1].strip()

        elif "Bit Rates:" in line:
            current.setdefault('bit_rates', []).append(
                line.split("Bit Rates:")[-1].strip()
            )

        elif line.startswith("IE:"):
            current.setdefault('ie', []).append(
                line.replace("IE:", "").strip()
            )

        elif "Extra:" in line:
            current.setdefault('extra', []).append(
                line.replace("Extra:", "").strip()
            )

    if current:
        networks.append(current)

    return networks


def scan_wifi(interface):
    print("\n" + "="*60)
    print(f"WI-FI SCAN - Interface: {interface}")
    print("="*60)

    # Interface information.
    try:
        iw_info = subprocess.run(
            ["iw", "dev", interface, "info"],
            capture_output=True, text=True
        )
        print("Interface Info:")
        for line in iw_info.stdout.strip().splitlines():
            print(f"  {line}")
        print()
    except Exception:
        pass

    # Scan networks.
    print("Scanning for Wi-Fi networks...\n")
    try:
        result = subprocess.run(
            ["iwlist", interface, "scan"],
            capture_output=True, text=True, timeout=30
        )

        if "Interface doesn't support scanning" in result.stderr:
            print(f"Interface {interface} does not support scanning.")
            return

        networks = parse_iwlist(result.stdout)

        if not networks:
            print("No network found.")
            return

        # Sort by signal strength.
        def signal_sort(n):
            try:
                return float(n.get('signal', '0').replace(' dBm', ''))
            except Exception:
                return 0

        networks.sort(key=signal_sort, reverse=True)

        print(f"Found {len(networks)} network(s):\n")

        for i, net in enumerate(networks, 1):
            print(f"{'-'*50}")
            print(f"[{i:02d}] SSID       : {net.get('ssid', 'N/A')}")
            print(f"     BSSID (MAC): {net.get('bssid', 'N/A')}")
            print(f"     Channel    : {net.get('channel', 'N/A')}")
            print(f"     Frequency  : {net.get('frequency', 'N/A')}")
            print(f"     Signal     : {net.get('signal', 'N/A')} dBm")
            print(f"     Quality    : {net.get('quality', 'N/A')}")
            print(f"     Encryption : {net.get('encryption', 'N/A')}")
            print(f"     Mode       : {net.get('mode', 'N/A')}")

            if net.get('bit_rates'):
                print(f"     Bit Rates  : {', '.join(net['bit_rates'])}")

            if net.get('ie'):
                print("     IE Info    :")
                for ie in net['ie']:
                    print(f"       - {ie}")

            if net.get('extra'):
                print("     Extra      :")
                for ex in net['extra']:
                    print(f"       - {ex}")
            print()

    except subprocess.TimeoutExpired:
        print("Wi-Fi scan timed out.")
    except FileNotFoundError:
        print("iwlist not found: sudo apt install wireless-tools")
    except Exception as e:
        print(f"Error: {e}")


def find_monitor_interface():
    """Return the first monitor-mode interface found, if any."""
    try:
        result = subprocess.run(["iw", "dev"], capture_output=True, text=True)
        current_iface = None
        current_type = None

        for raw in result.stdout.splitlines():
            line = raw.strip()
            if line.startswith("Interface "):
                if current_iface and current_type == "monitor":
                    return current_iface
                current_iface = line.split()[-1]
                current_type = None
            elif line.startswith("type "):
                current_type = line.split()[-1]

        if current_iface and current_type == "monitor":
            return current_iface
    except Exception:
        pass

    return None


def scan_associated_wifi_clients(interface):
    """Show stations associated to the informed Wi-Fi interface."""
    print("\n" + "="*60)
    print(f"WI-FI CLIENTS (ASSOCIATED) - Interface: {interface}")
    print("="*60)

    try:
        result = subprocess.run(
            ["iw", "dev", interface, "station", "dump"],
            capture_output=True, text=True, timeout=20
        )

        if result.returncode != 0:
            print("Could not read associated stations on this interface.")
            if result.stderr:
                print(f"Details: {result.stderr.strip()}")
            return

        lines = [l.rstrip() for l in result.stdout.splitlines() if l.strip()]
        if not lines:
            print("No associated client found.")
            print("Hint: this usually works when the interface is operating as AP.")
            return

        clients = []
        current = {}
        for line in lines:
            s = line.strip()
            if s.startswith("Station "):
                if current:
                    clients.append(current)
                parts = s.split()
                current = {"mac": parts[1] if len(parts) > 1 else "N/A"}
                continue

            if ":" in s and current:
                key, value = s.split(":", 1)
                current[key.strip().lower()] = value.strip()

        if current:
            clients.append(current)

        if not clients:
            print("No associated client found.")
            return

        print(f"Found {len(clients)} associated client(s):\n")
        for idx, client in enumerate(clients, 1):
            print(f"{'-'*50}")
            print(f"[{idx:02d}] Client MAC : {client.get('mac', 'N/A')}")
            print(f"     Signal     : {client.get('signal', 'N/A')}")
            print(f"     TX bitrate : {client.get('tx bitrate', 'N/A')}")
            print(f"     RX bitrate : {client.get('rx bitrate', 'N/A')}")
            print(f"     Connected  : {client.get('connected time', 'N/A')} s")
            print()

    except subprocess.TimeoutExpired:
        print("Associated client scan timed out.")
    except FileNotFoundError:
        print("iw not found: sudo apt install iw")
    except Exception as e:
        print(f"Error: {e}")


def scan_wifi_connection_attempts(duration=15):
    """Capture probe/auth/association frames to reveal clients trying to connect."""
    print("\n" + "="*60)
    print("WI-FI CLIENT ATTEMPTS (MONITOR MODE)")
    print("="*60)

    if not shutil.which("tshark"):
        print("tshark not found: sudo apt install tshark")
        return

    monitor_iface = find_monitor_interface()
    if not monitor_iface:
        print("No monitor-mode interface found.")
        print("Hint: create one and re-run this script.")
        print("Example: sudo iw dev <iface> interface add mon0 type monitor")
        print("         sudo ip link set mon0 up")
        return

    print(f"Using monitor interface: {monitor_iface}")
    print(f"Capturing client attempts for {duration} seconds...\n")

    display_filter = (
        "wlan.fc.type_subtype==4 || "
        "wlan.fc.type_subtype==11 || "
        "wlan.fc.type_subtype==0"
    )

    cmd = [
        "tshark", "-i", monitor_iface, "-l",
        "-a", f"duration:{duration}",
        "-Y", display_filter,
        "-T", "fields",
        "-E", "separator=\t",
        "-e", "frame.time",
        "-e", "wlan.sa",
        "-e", "wlan.da",
        "-e", "wlan.bssid",
        "-e", "wlan.ssid",
        "-e", "wlan.fc.type_subtype",
    ]

    subtype_names = {
        "0": "Association Request",
        "4": "Probe Request",
        "11": "Authentication",
    }

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=duration + 10,
        )

        if result.returncode not in (0, 1):
            print("Failed to capture monitor-mode packets.")
            if result.stderr:
                print(f"Details: {result.stderr.strip()}")
            return

        events = []
        for line in result.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) < 6:
                continue

            when, src, dst, bssid, ssid, subtype = [p.strip() for p in parts[:6]]
            if not src or src.lower() == "ff:ff:ff:ff:ff:ff":
                continue

            events.append({
                "time": when,
                "client": src,
                "dst": dst if dst else "N/A",
                "bssid": bssid if bssid else "N/A",
                "ssid": ssid if ssid else "<broadcast/unknown>",
                "event": subtype_names.get(subtype, f"Subtype {subtype}"),
            })

        if not events:
            print("No client connection attempt detected in the capture window.")
            return

        unique_clients = {e["client"] for e in events}
        print(f"Detected {len(events)} frame(s) from {len(unique_clients)} client(s):\n")

        for idx, event in enumerate(events, 1):
            print(f"{'-'*50}")
            print(f"[{idx:02d}] Time   : {event['time']}")
            print(f"     Event  : {event['event']}")
            print(f"     Client : {event['client']}")
            print(f"     SSID   : {event['ssid']}")
            print(f"     BSSID  : {event['bssid']}")
            print(f"     Target : {event['dst']}")
            print()

    except subprocess.TimeoutExpired:
        print("Monitor-mode capture timed out.")
    except Exception as e:
        print(f"Error while capturing client attempts: {e}")


# Main entry point
async def main():
    check_root()

    print("\n" + "="*60)
    print("  BLUETOOTH AND WI-FI SCANNER")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("="*60)

    # Bluetooth Classic
    scan_bluetooth_classic_hci()

    # Bluetooth LE
    await scan_bluetooth_le()

    # Wi-Fi
    iface = get_wifi_interface()
    if iface:
        scan_wifi(iface)
        scan_associated_wifi_clients(iface)
        scan_wifi_connection_attempts(duration=15)
    else:
        print("\nNo Wi-Fi interface found.")
        print("Check with: iw dev")

    print("\n" + "="*60)
    print("SCAN COMPLETED")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

