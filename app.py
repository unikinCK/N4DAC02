from flask import Flask, request, jsonify, render_template, redirect, url_for
from pymodbus.client import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder
import paho.mqtt.client as mqtt
import json
import os
import signal

app = Flask(__name__)

# Configuration for Modbus device
MODBUS_HOST = '192.168.0.184'  # Default Modbus device IP
MODBUS_PORT = 502             # Default Modbus TCP port
UNIT_ID = 1                   # Default RS485 address of your device
MODBUS_CONNECTED = True       # Connection status for Modbus

# Configuration for MQTT
MQTT_BROKER = '192.168.0.180'  # Replace with your MQTT broker address
MQTT_PORT = 1883               # Default MQTT port
MQTT_CONNECTED = True          # Connection status for MQTT

# -- Central place to define the "base" topic --
MQTT_BASE_TOPIC = 'modbus'  # Change this if you want a different root
MQTT_CONTROL_TOPIC = f"{MQTT_BASE_TOPIC}/control"
MQTT_STATE_TOPIC   = f"{MQTT_BASE_TOPIC}/state"

# Create Modbus client
def create_modbus_client():
    return ModbusTcpClient(MODBUS_HOST, port=MODBUS_PORT)

client = create_modbus_client()

def check_modbus_connection():
    global MODBUS_CONNECTED
    try:
        client.connect()
        MODBUS_CONNECTED = client.is_socket_open()
        client.close()
    except Exception as e:
        print(f"Error connecting to Modbus server: {e}")
        MODBUS_CONNECTED = False


def on_connect(client, userdata, flags, rc):
    """
    Called when the MQTT client connects to the broker.
    We subscribe ONLY to the control topic, e.g. "modbus/control/#".
    """
    if rc == 0:
        print("Connected to MQTT broker successfully.")
        client.subscribe(f"{MQTT_CONTROL_TOPIC}/#")
        print(f"Subscribed to topic: {MQTT_CONTROL_TOPIC}/#")
    else:
        print(f"Failed to connect to MQTT broker. Code: {rc}")


# Create MQTT client with updated API
mqtt_client = mqtt.Client(protocol=mqtt.MQTTv311)
mqtt_client.on_connect = on_connect

def check_mqtt_connection():
    global MQTT_CONNECTED
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
        mqtt_client.loop_start()
        MQTT_CONNECTED = True
    except Exception as e:
        print(f"Error starting MQTT client: {e}")
        MQTT_CONNECTED = False


def on_message(client, userdata, msg):
    """
    Ignore any message published to the STATE topic to prevent
    re-triggering ourselves (feedback loop).
    """
    if msg.topic.startswith(MQTT_STATE_TOPIC):
        return

    print(f"Received message on topic {msg.topic}: {msg.payload.decode()}")
    try:
        payload = json.loads(msg.payload.decode())
        channel = payload.get('channel')
        voltage = payload.get('voltage')

        if channel not in [1, 2]:
            print(f"Invalid channel received: {channel}")
            return

        if not isinstance(voltage, (int, float)):
            print(f"Invalid voltage format received: {voltage}")
            return

        print(f"Received MQTT message to set voltage: Channel {channel}, Voltage {voltage}")

        # Set voltage on the Modbus device
        success = modbus_set_voltage(channel, voltage)
        if success:
            print(f"Successfully set Modbus voltage: Channel {channel}, Voltage {voltage}")
            # Publish the new voltages to the STATE topic
            safe_publish_voltage()
        else:
            print(f"Failed to set Modbus voltage: Channel {channel}, Voltage {voltage}")
    except json.JSONDecodeError:
        print("Invalid JSON payload received.")
    except Exception as e:
        print(f"Error processing MQTT message: {e}")

mqtt_client.on_message = on_message

def modbus_read_voltage(channel):
    """Read the voltage from a specified channel."""
    try:
        address = 0x0000 if channel == 1 else 0x0001
        client.connect()
        response = client.read_holding_registers(address, count=1, slave=UNIT_ID)
        client.close()
        if response and response.registers:
            voltage_raw = response.registers[0]
            return voltage_raw * 0.01
    except Exception as e:
        print(f"Error reading Modbus channel {channel}: {e}")
    return None

def safe_publish_voltage():
    """Publish both channel voltages to the STATE topic, e.g. 'modbus/state/channel_x'."""
    if not MQTT_CONNECTED:
        print("MQTT not connected. Skipping publish.")
        return

    for channel in [1, 2]:
        voltage = modbus_read_voltage(channel)
        if voltage is not None:
            # Publish to the STATE topic
            mqtt_client.publish(
                f"{MQTT_STATE_TOPIC}/channel_{channel}",
                json.dumps({"channel": channel, "voltage": voltage})
            )
            print(f"Published voltage for channel {channel}: {voltage}V")

def modbus_set_voltage(channel, voltage):
    """Set the voltage for a specified channel."""
    if not (0.00 <= voltage <= 5.0 if channel == 1 else 0.0 <= voltage <= 10.0):
        print(f"Voltage {voltage} out of range for channel {channel}.")
        return False
    try:
        voltage_raw = int(voltage * 100)
        address = 0x0000 if channel == 1 else 0x0001
        client.connect()
        response = client.write_register(address, voltage_raw, slave=UNIT_ID)
        client.close()
        if response is not None:
            # Optionally publish updated voltage after successful write
            safe_publish_voltage()
            return True
    except Exception as e:
        print(f"Error setting Modbus channel {channel} to {voltage}V: {e}")
    return False


@app.route('/get_voltage', methods=['GET'])
def get_voltage():
    """Retrieve the current voltage for a specified channel."""
    channel = request.args.get('channel', type=int)
    if channel not in [1, 2]:
        return jsonify({"error": "Invalid channel. Use 1 or 2."}), 400

    voltage = modbus_read_voltage(channel)
    if voltage is None:
        return jsonify({"error": "Failed to read voltage."}), 500

    return jsonify({"channel": channel, "voltage": voltage})


@app.route('/')
def index():
    """Render the start page with the functionality overview and voltage controls."""
    try:
        voltage_1 = modbus_read_voltage(1)
        voltage_2 = modbus_read_voltage(2)
    except Exception as e:
        print(f"Error reading initial voltages: {e}")
        voltage_1 = None
        voltage_2 = None

    voltage_1 = voltage_1 if voltage_1 is not None else "N/A"
    voltage_2 = voltage_2 if voltage_2 is not None else "N/A"

    return render_template(
        'homepage_template.jinja',
        voltage_1=voltage_1,
        voltage_2=voltage_2,
        host=MODBUS_HOST,
        port=MODBUS_PORT,
        unit_id=UNIT_ID,
        mqtt_broker=MQTT_BROKER,
        mqtt_port=MQTT_PORT,
        mqtt_connected=MQTT_CONNECTED,
        modbus_connected=MODBUS_CONNECTED,

        # Pass the current base topic so we can display it
        mqtt_base_topic=MQTT_BASE_TOPIC
    )



@app.route('/set_voltage', methods=['POST', 'GET'])
def set_voltage():
    """Set the output voltage for a specified channel via JSON payload or query parameters."""
    if request.method == 'POST':
        data = request.json  # Parse JSON payload
        if not data:
            return jsonify({"error": "Invalid JSON payload."}), 400

        channel = data.get('channel')
        voltage = data.get('voltage')

    elif request.method == 'GET':
        # Parse query parameters
        channel = request.args.get('channel', type=int)
        voltage = request.args.get('voltage', type=float)

    # Validate inputs
    if not isinstance(channel, int) or not isinstance(voltage, (int, float)):
        return jsonify({"error": "Invalid channel or voltage format."}), 400

    if channel not in [1, 2]:
        return jsonify({"error": "Invalid channel. Use 1 or 2."}), 400

    # Attempt to set the voltage
    success = modbus_set_voltage(channel, voltage)
    if success:
        return jsonify({"message": "Voltage set successfully.", "channel": channel, "voltage": voltage})
    else:
        return jsonify({"error": "Failed to set voltage."}), 500



@app.route('/set_voltage_form', methods=['POST'])
def set_voltage_form():
    """Set the output voltage for a specified channel via form submission."""
    try:
        channel = int(request.form.get('channel'))
        voltage = float(request.form.get('voltage'))
    except (TypeError, ValueError):
        return redirect(url_for('index'))  # Redirect back to homepage on error

    if channel not in [1, 2]:
        return redirect(url_for('index'))  # Redirect back to homepage on error

    success = modbus_set_voltage(channel, voltage)
    return redirect(url_for('index'))  # Always redirect to homepage


@app.route('/update_config', methods=['POST'])
def update_config():
    """Update the Modbus configuration."""
    global MODBUS_HOST, MODBUS_PORT, UNIT_ID, client

    MODBUS_HOST = request.form.get('host')
    MODBUS_PORT = int(request.form.get('port'))
    UNIT_ID = int(request.form.get('unit_id'))

    # Reinitialize the Modbus client
    client = create_modbus_client()
    check_modbus_connection()

    return jsonify({"message": "Modbus configuration updated.", 
                    "host": MODBUS_HOST, 
                    "port": MODBUS_PORT, 
                    "unit_id": UNIT_ID})


@app.route('/update_mqtt', methods=['POST'])
def update_mqtt():
    """Update the MQTT configuration."""
    global MQTT_BROKER, MQTT_PORT

    MQTT_BROKER = request.form.get('mqtt_broker')
    MQTT_PORT = int(request.form.get('mqtt_port'))

    # Check MQTT connection
    check_mqtt_connection()

    return jsonify({"message": "MQTT configuration updated.", 
                    "broker": MQTT_BROKER, 
                    "port": MQTT_PORT})


# Load API definition from JSON for /api_doc
with open('api_definition.json', 'r', encoding='utf-8') as f:
    API_DEFINITION = json.load(f)


@app.route('/api_doc', methods=['GET'])
def api_doc():
    """Display the RESTful API documentation."""
    return render_template('api_doc_template.jinja', api_definition=API_DEFINITION)

@app.route('/update_mqtt_topic', methods=['POST'])
def update_mqtt_topic():
    """
    Update the MQTT base topic (e.g. from 'modbus' to something else).
    This automatically adjusts MQTT_CONTROL_TOPIC and MQTT_STATE_TOPIC,
    unsubscribes from the old control topic, and re-subscribes to the new one.
    """
    global MQTT_BASE_TOPIC, MQTT_CONTROL_TOPIC, MQTT_STATE_TOPIC, mqtt_client
    
    # -- 1) Read user input --
    # Depending on how you send the data, you can use either form or JSON.
    # Example using form data:
    new_base_topic = request.form.get('base_topic', '').strip()
    
    # Alternatively, if you prefer JSON:
    # data = request.get_json()
    # new_base_topic = data.get('base_topic', '').strip() if data else ''
    
    if not new_base_topic:
        return jsonify({"error": "Base topic cannot be empty."}), 400

    # -- 2) Unsubscribe from old control topic if connected --
    if MQTT_CONNECTED:
        try:
            mqtt_client.unsubscribe(f"{MQTT_CONTROL_TOPIC}/#")
            print(f"Unsubscribed from old topic: {MQTT_CONTROL_TOPIC}/#")
        except Exception as e:
            print(f"Error unsubscribing from {MQTT_CONTROL_TOPIC}/#: {e}")

    # -- 3) Update the global variables --
    MQTT_BASE_TOPIC = new_base_topic
    MQTT_CONTROL_TOPIC = f"{MQTT_BASE_TOPIC}/control"
    MQTT_STATE_TOPIC = f"{MQTT_BASE_TOPIC}/state"

    # -- 4) Re-subscribe to the new control topic if connected --
    if MQTT_CONNECTED:
        try:
            mqtt_client.subscribe(f"{MQTT_CONTROL_TOPIC}/#")
            print(f"Re-subscribed to new topic: {MQTT_CONTROL_TOPIC}/#")
        except Exception as e:
            print(f"Error subscribing to {MQTT_CONTROL_TOPIC}/#: {e}")

    return jsonify({
        "message": "MQTT base topic updated.",
        "base_topic": MQTT_BASE_TOPIC,
        "control_topic": MQTT_CONTROL_TOPIC,
        "state_topic": MQTT_STATE_TOPIC
    })

@app.route('/restart_server', methods=['POST'])
def restart_server():
    """Restart the Flask server."""
    try:
        # Send the signal to the current process to terminate it gracefully
        os.kill(os.getpid(), signal.SIGINT)
        return jsonify({"message": "Server is restarting..."}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to restart server: {e}"}), 500

if __name__ == '__main__':
    # Check connections
    check_modbus_connection()
    check_mqtt_connection()

    # Publish initial voltage on startup
    if MQTT_CONNECTED:
        safe_publish_voltage()

    # Start the Flask app
    app.run(host='0.0.0.0', port=5000)
