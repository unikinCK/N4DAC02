
# Modbus + MQTT Control App

This application provides a Flask-based web interface for configuring and controlling a N4DAC02 Modbus device, as well as publishing and subscribing to MQTT messages. Users can:

- **Read and set voltages** on Modbus channels.
- **Monitor connection statuses** for both Modbus and MQTT.
- **Update Modbus and MQTT configuration** on-the-fly.
- **Define and view RESTful API endpoints** via a dedicated documentation page (`/api_doc`).

---

## Features

### Set Voltage
- Set voltage for Channel 1 or Channel 2 via form submission or JSON.

### MQTT Integration
- **Control messages:** `{MQTT_BASE_TOPIC}/control/...`
- **State/voltage updates:** `{MQTT_BASE_TOPIC}/state/...`

### Modbus
- Communicates via Modbus TCP to read/write holding registers.

---

## Configuration Endpoints
- `/update_config` — Update host/port/unit_id for Modbus.
- `/update_mqtt` — Update MQTT broker and port.
- `/update_mqtt_topic` — Change the base topic (default: `modbus`).

### RESTful API Docs
- `/api_doc` — Displays all endpoints and parameters from a JSON definition file.

---

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/<repository-name>.git
cd <repository-name>
```

### 2. Requirements
- Python 3.10+ (recommended)
- pip (Python package manager)
- Docker (optional, if you plan to build/use the Docker image)

### 3. Installation (Local)

#### Create and activate a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate
```

#### Install dependencies:
```bash
pip install -r requirements.txt
```

#### Set up your default configuration in `app.py` (e.g., Modbus IP, MQTT broker, etc.).

#### Run the application:
```bash
python app.py
```

Open a browser to [http://localhost:5000](http://localhost:5000) to see the interface.

---

### 4. Using Docker

#### Download the Docker image:
```bash
docker pull unikin/modbus-app
```

#### Build the Docker image:
```bash
docker build -t modbus-app .
```

#### Run the container:
```bash
docker run -d -p 5000:5000 --name modbus_container modbus-app
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## Configuration Overview

### Modbus
- **Default IP:** `192.168.0.101`
- **Default Port:** `502`
- **Default Unit ID:** `1`
- Update these at runtime under "Update Modbus Configuration" or via the `/update_config` endpoint.

### MQTT
- **Default Broker:** `192.168.0.180`
- **Default Port:** `1883`
- **Default Base Topic:** `modbus`
- Update broker/port under "MQTT Configuration" or via the `/update_mqtt` endpoint.
- Change the base topic (`MQTT_BASE_TOPIC`) under "Update MQTT Base Topic" or via the `/update_mqtt_topic` endpoint.

---

## RESTful API

### `/api_doc`
Displays generated documentation using `api_definition.json`.

### `/get_voltage` (GET)
- **Example:** `/get_voltage?channel=1`
- **Returns:** JSON with current voltage for the specified channel.

### `/set_voltage` (POST, JSON)
- **Example JSON payload:**
  ```json
  {
    "channel": 1,
    "voltage": 3.5
  }
  ```
- Sets the specified channel’s voltage, returns success/failure JSON.

Additional endpoints are listed in `api_definition.json` and appear on the `/api_doc` page.

---

## Project Structure
```
.
├── app.py                     # Main Flask application
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker configuration
├── api_definition.json        # RESTful API definitions for /api_doc
├── templates/
│   ├── homepage_template.jinja    # Main interface
│   ├── api_doc_template.jinja     # API documentation
└── README.md                  # This file
```

---

## Contributing
1. Fork the repo and create your feature branch.
2. Commit your changes with clear messages.
3. Push to your branch.
4. Open a Pull Request.

---

## License
MIT License – feel free to adapt and use this code as needed.

---

Enjoy using the **Modbus + MQTT Control App**! If you run into any issues, please open an issue or submit a pull request.
