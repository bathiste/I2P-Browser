# I2P Browser

A simple desktop web browser for browsing websites on the I2P network.

## Features

- Browse `.i2p` websites
- Built-in tab management
- HTTP and HTTPS proxy support
- JavaScript control
- Cookie filtering
- Network inspector
- I2P proxy status checker
- I2P router console access

## Requirements

- Python 3
- PyQt5
- PyQtWebEngine
- I2P router running locally

## Installation

```bash
pip install PyQt5 PyQtWebEngine
```

## Usage

Start your I2P router, then launch the browser:

```bash
python main.py
```

Default I2P settings:

- HTTP Proxy: `127.0.0.1:4444`
- HTTPS Proxy: `127.0.0.1:4445`
- Router Console: `http://127.0.0.1:7657/`

This project isn't affiliated with the I2P project and is a independent project
