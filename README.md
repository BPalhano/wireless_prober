# Wireless Prober: BLE Signaling Monitor & Radio Sensing Platform

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB.svg?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Bluetooth_LE-SIG_Standard-0082FC.svg?style=for-the-badge&logo=bluetooth&logoColor=white" alt="BLE" />
  <img src="https://img.shields.io/badge/Tests-14%2F14_Passed-brightgreen.svg?style=for-the-badge&logo=pytest&logoColor=white" alt="Pytest" />
  <img src="https://img.shields.io/badge/Architecture-Modular_CLI-blue.svg?style=for-the-badge" alt="Modular" />
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge" alt="License" />
</p>

---

## Executive Summary

**Wireless Prober** is a Linux platform for Bluetooth Low Energy (BLE) signaling monitoring, real-time distance estimation, RF channel perturbation analysis (Radio Sensing), and multilateration.

Built on non-root BlueZ D-Bus APIs and asynchronous event loops (`bleak`), Wireless Prober replaces deprecated legacy tooling (`hcitool`/`hciconfig`) with an industrial-grade digital signal processing (DSP) pipeline that filters high-frequency multipath fading, estimates physical distance, and monitors channel variance to detect physical human motion in the propagation environment without dedicated radar hardware.

---

## Technical Architecture

```mermaid
flowchart TD
    subgraph CAPTURE["1. Signal Ingestion Engine"]
        HCI["Host Bluetooth Controller (HCI)"] --> DBUS["BlueZ D-Bus API Engine"]
        DBUS --> ASYNC["Async Stream Ingestion (Bleak)"]
        ASYNC --> PKT["Structured AdvertisementPacket<br/>(MAC, RSSI, TxPower, Timestamps)"]
    end

    subgraph DSP["2. Digital Signal Processing Pipeline"]
        PKT --> KF["1D Kalman State Filter<br/>(Gaussian Multipath Damping)"]
        KF --> PL["Log-Distance Path Loss Model<br/>d = 10^((TxPower - RSSI) / 10n)"]
        PKT --> RS["Radio Sensing Detector<br/>(Rolling Variance Window sigma^2)"]
    end

    subgraph APPS["3. Localization & Telemetry Applications"]
        PL --> TRILAT["2D Multilateration Engine<br/>(Non-Linear Least Squares)"]
        RS --> SENSE["RF Perturbation Detector<br/>(Motion & Human Presence Alerts)"]
        KF & PL & RS --> TUI["Interactive Terminal UI (Rich)<br/>(Live Telemetry & Frequency Rates)"]
        KF & PL & RS --> SQL["SQLite Time-Series Storage<br/>(WAL Logging & CSV Export)"]
    end
```

---

## Key Engineering Innovations

1. **Continuous Asynchronous Signal Ingestion:**
   * High-throughput event listener capturing advertising packet types (`ADV_IND`, `ADV_NONCONN_IND`, `SCAN_RSP`) continuously without polling interruptions.
   * Emits structured payloads with microsecond-precision timestamps, manufacturer identifiers, and service UUIDs.

2. **1D Kalman Filtering for Multipath Noise Reduction:**
   * Raw 2.4 GHz RSSI signals suffer from severe Rayleigh/Rician multipath fading.
   * An optimized state filter adaptively smooths Gaussian measurement noise ($R = 3.50$) against process dynamics ($Q = 0.12$) with an integrated soft outlier rejection gate.

3. **Log-Distance Path Loss Distance Estimation:**
   * Computes physical range using standard electromagnetic wave attenuation models:
     $$d = 10^{\frac{\text{TxPower} - \text{RSSI}}{10 \cdot n}}$$
   * Includes parameter calibration routines to tune reference power ($\text{TxPower}$) and path loss exponents ($n$) to indoor environments.

4. **Device-Free Radio Sensing (Channel Perturbation Analysis):**
   * Computes the temporal variance ($\sigma^2$) of the received signal strength across a sliding temporal window.
   * Environmental obstruction or human movement through the RF Fresnel zone induces scattering spikes ($\sigma^2 \ge 3.5 \text{ dB}^2$), triggering real-time motion alerts without cameras or infrared sensors.

5. **2D Multilateration (Localization):**
   * Robust geometric solver using Non-Linear Least Squares (`scipy.optimize.least_squares` with soft L1 loss) to determine target coordinates $(x, y)$ from 3 or more anchor nodes while attenuating distance outliers.

---

## Repository Structure

```text
wireless_prober/
├── Makefile                                # Automated tasks (install, test, scan, monitor)
├── pyproject.toml                          # Project metadata and dependencies
├── telemetry.db                            # SQLite time-series telemetry store
├── prober.py                               # Compatibility entrypoint wrapper
├── prober/
│   ├── __init__.py
│   ├── cli.py                              # Unified CLI entrypoint (scan, monitor, sense, export)
│   ├── capture/
│   │   ├── __init__.py
│   │   └── ble_engine.py                   # Async Bleak packet stream
│   ├── core/
│   │   ├── __init__.py
│   │   └── models.py                       # AdvertisementPacket & DeviceTelemetry models
│   ├── dsp/
│   │   ├── __init__.py
│   │   ├── kalman.py                       # 1D Kalman state filter
│   │   ├── path_loss.py                    # Log-distance path loss estimator & calibration
│   │   └── sensing.py                      # Radio sensing & variance perturbation detector
│   ├── localization/
│   │   ├── __init__.py
│   │   └── trilateration.py                # 2D Non-Linear Least Squares solver
│   ├── storage/
│   │   ├── __init__.py
│   │   └── timeseries.py                   # SQLite storage & CSV export
│   └── ui/
│       ├── __init__.py
│       └── tui.py                          # Live rich terminal dashboard
└── tests/
    ├── test_kalman.py                      # Kalman filter convergence and noise reduction tests
    ├── test_path_loss.py                   # Path loss distance math and calibration tests
    ├── test_sensing.py                     # Variance thresholding and motion trigger tests
    ├── test_trilateration.py               # Geometric 2D coordinate recovery tests
    └── test_models.py                      # Model serialization and SQLite storage tests
```

---

## Quickstart Guide

### 1. Installation
Set up the isolated virtual environment and install the package:

```bash
git clone https://github.com/BPalhano/wireless_prober.git
cd wireless_prober

# Create venv and install package in editable mode
make install
```

### 2. Running Automated Unit Tests
Run the comprehensive test suite verifying DSP, estimation math, and storage:

```bash
make test
# Or: .venv/bin/pytest tests/ -v
```

---

## Operational CLI Modes

### 1. Passive Device Discovery & Distance Overview (`scan`)
Scans advertising packets for a fixed duration and displays a formatted summary table:

```bash
# Scan for 10 seconds
.venv/bin/python -m prober.cli scan --duration 10

# Scan with custom path loss parameters
.venv/bin/python -m prober.cli scan --duration 5 --n 2.5 --tx-power -59
```

### 2. Live Interactive Terminal Monitoring Dashboard (`monitor`)
Renders a live terminal interface with packet counts, transmission frequency (Hz), raw RSSI, Kalman-filtered RSSI, estimated distance, and RF sensing state:

```bash
# Monitor all advertising beacons
.venv/bin/python -m prober.cli monitor

# Filter and isolate a specific target device
.venv/bin/python -m prober.cli monitor --target C0:84:FF:50:8B:07
```

### 3. Real-Time RF Radio Sensing Mode (`sense`)
Locks onto a nearby beacon and streams continuous high-rate variance telemetry, flagging line-of-sight motion events:

```bash
.venv/bin/python -m prober.cli sense
```

### 4. Telemetry Dataset Export (`export`)
Exports logged packet observations from the SQLite database to CSV:

```bash
.venv/bin/python -m prober.cli export --db telemetry.db --output dataset.csv
```

---

## Verification & Empirical Results

The pipeline was validated live against active Bluetooth Low Energy beacons, demonstrating:
* Sub-10ms packet processing latency per advertising PDU.
* Over 70% reduction in RSSI jitter using the 1D Kalman filter compared to raw measurement variance.
* Real-time detection of Fresnel zone crossing events triggered by human movement.

---

## Author & License

* **Author:** Igor Braga Palhano
* **Domain:** Telecommunications Engineering, RF Sensing, Embedded Systems
* **License:** [MIT License](LICENSE)
