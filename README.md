# RF Listener

A concise Bluetooth and Wi-Fi reconnaissance script for Linux.

This project scans:
- Bluetooth Classic devices (via `hcitool` / `hciconfig`)
- Bluetooth Low Energy (BLE) advertisements (via `bleak`)
- Wi-Fi access points (via `iwlist`)
- Wi-Fi clients:
  - associated stations (via `iw station dump`)
  - connection attempts in monitor mode (via `tshark`)

## Requirements

- Linux
- Python 3.13+ (or compatible)
- Root privileges for full scanning

## System Dependencies

Install required system packages:

```bash
sudo apt update
sudo apt install -y bluez wireless-tools iw tshark
```

Notes:
- `bluez` provides `hcitool`, `hciconfig`, `sdptool`, and Bluetooth service components.
- `wireless-tools` provides `iwlist`.
- `iw` is used for interface detection and station dump.
- `tshark` is used to detect Wi-Fi client connection attempts in monitor mode.

## Python Dependency

From the workspace root (`/home/igor/Documents`), activate your virtual environment and install:

```bash
source ./env/bin/activate
python -m pip install bleak
```

## One Command to Run Everything

From `/home/igor/Documents`:

```bash
source ./env/bin/activate && sudo ./env/bin/python RF_listener/prober.py
```

## Monitor Mode (Optional but Recommended)

To detect Wi-Fi connection attempts (probe/auth/association), you need a monitor-mode interface.

Example:

```bash
sudo iw dev <iface> interface add mon0 type monitor
sudo ip link set mon0 up
```

Then run the script again.

## Output Summary

The script prints sections for:
- Bluetooth Classic scan
- BLE scan
- Wi-Fi network scan
- Associated Wi-Fi clients
- Wi-Fi client connection attempts (when monitor mode + `tshark` are available)
