import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import paho.mqtt.client as mqtt
import json
import threading
import logging

# ----------- MQTT CONFIG -----------
MQTT_BROKER = "ca4474eebd934b0abb85f0c60addd359.s1.eu.hivemq.cloud"  # change this to your ESP broker IP
MQTT_PORT = 883
MQTT_USERNAME = "charlie"
MQTT_PASSWORD = "s#Cn5!wswNMF.Kj"
TOPIC_TIME = "esp32/time_range"
TOPIC_SENSOR = "esp32/motion"

# Shared variable for latest sensor data
latest_detection = {"status": "Waiting for data..."}

# ----------- MQTT CALLBACKS -----------
def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Connected with result code {rc}")
    client.subscribe(TOPIC_SENSOR)

def on_message(client, userdata, msg):
    try:
        data = msg.payload
        logging.info(f"Received data: {data}")
        if "motion_detected" in data:
            latest_detection["status"] = (
                "ALERT! Person Detected!" if data["detected"] else "No Person Detected"
            )
        else:
            latest_detection["status"] = f"⚠️ Invalid message: {data}"
    except Exception as e:
        latest_detection["status"] = f"⚠️ Error parsing: {e}"

def mqtt_loop():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

# Start MQTT thread
threading.Thread(target=mqtt_loop, daemon=True).start()

# Separate MQTT client for publishing
pub_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
pub_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
pub_client.connect(MQTT_BROKER, MQTT_PORT, 60)
pub_client.loop_start()

# ----------- DASH APP -----------
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])

hours = [{"label": f"{i:02d}", "value": i} for i in range(24)]
minutes = [{"label": f"{i:02d}", "value": i} for i in range(0, 60, 5)]

app.layout = dbc.Container([
    html.H3("S.E.A.L", className="text-center mt-4 mb-2"),
    dbc.Card([
        dbc.CardBody([
            html.Label("Start Time", className="fs-5"),
            dbc.Row([
                dbc.Col([
                    html.Label("Hour", className=" small"),
                    dcc.Dropdown(id="start-hour", options=hours, value=8, clearable=False),
                ], width=6),
                dbc.Col([
                    html.Label("Minute", className=" small"),
                    dcc.Dropdown(id="start-minute", options=minutes, value=0, clearable=False),
                ], width=6),
            ], className="mb-2"),

            html.Label("End Time", className="fs-5"),
            dbc.Row([
                dbc.Col([
                    html.Label("Hour", className=" small"),
                    dcc.Dropdown(id="end-hour", options=hours, value=12, clearable=False),
                ], width=6),
                dbc.Col([
                    html.Label("Minute", className=" small"),
                    dcc.Dropdown(id="end-minute", options=minutes, value=0, clearable=False),
                ], width=6),
            ], className="mb-2"),

            dbc.Button("Set Time", id="send-btn", color="primary", className="mt-2 w-100"),
            html.Div(" ", id="status", className="text-center text-alert mt-3 fs-5"),

        ])
    ], className="shadow-lg border-0 rounded-3 mb-5 p-4"),

    dbc.Card([
        dbc.CardHeader("Person Detection", className="bg-secondary text-light fs-5"),
        dbc.CardBody([
            html.H4(id="result", className="text-center mt-3"),
            dcc.Interval(id="interval", interval=2000, n_intervals=0)  # Refresh every 2 sec
        ]),
    ], className="shadow-lg border-0 rounded-3 mb-5"),
], fluid=True)


@app.callback(
    Output("status", "children"),
    Input("send-btn", "n_clicks"),
    State("start-hour", "value"),
    State("start-minute", "value"),
    State("end-hour", "value"),
    State("end-minute", "value"),
    prevent_initial_call=True
)
def send_to_esp(n, start_h, start_m, end_h, end_m):
    if start_h is None or end_h is None:
        return "Please select valid times."
    
    payload = f"{start_h * 60 + start_m} {end_h * 60 + start_h}"

    try:
        pub_client.publish(TOPIC_TIME, payload)
        logging.info(f"Published data: {payload}")
        return f"Time Updated: {start_h:02d}:{start_m:02d} - {end_h:02d}:{end_m:02d}"
    except Exception as e:
        return f"Failed to send: {e}"


@app.callback(
    Output("result", "children"),
    Input("interval", "n_intervals")
)
def update_detection_display(_):
    return latest_detection["status"]


if __name__ == "__main__":
    app.run(debug=True, port=8050)
