from flask import Flask, jsonify
import random
import time
import requests
import os
import torch
import torch.nn as nn
import torch.optim as optim
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

sides = ['North', 'South', 'East', 'West']
vehicle_types = ['Car', 'Bus', 'Truck', 'Bike']

# Target APIs for each traffic point
target_flask_apis = [
    "http://localhost:5001/get-traffic-signal",
    "http://localhost:5002/get-traffic-signal",
    "http://localhost:5003/get-traffic-signal",
    "http://localhost:5004/get-traffic-signal",
    "http://localhost:5000/get-traffic-signal"
]

vehicle_priority = {
    'Car': 1,
    'Bus': 2,
    'Truck': 3,
    'Bike': 0.5
}

waiting_time_history = {side: 0 for side in sides}

# CNN model for traffic prediction
class TrafficCNN(nn.Module):
    def __init__(self):
        super(TrafficCNN, self).__init__()
        self.conv1 = nn.Conv2d(1, 16, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(16, 32, kernel_size=3, padding=1)
        self.fc1 = nn.Linear(32 * 4 * 4, 64)
        self.fc2 = nn.Linear(64, 4)

    def forward(self, x):
        x = torch.relu(self.conv1(x))
        x = torch.relu(self.conv2(x))
        x = x.view(x.size(0), -1)
        x = torch.relu(self.fc1(x))
        x = self.fc2(x)
        return x

# Initialize CNN model
model = TrafficCNN()
optimizer = optim.Adam(model.parameters(), lr=0.001)
criterion = nn.MSELoss()

# Function to adjust timing based on rush hours
def get_time_factor():
    current_hour = time.localtime().tm_hour
    return 1.5 if 7 <= current_hour <= 9 or 17 <= current_hour <= 19 else 1  # Rush hour factor

# Function to fetch traffic data from all Flask APIs
def fetch_traffic_data():
    aggregated_data = {side: {'vehicle_count': 0, 'vehicle_density': 0, 'priority': 0, 'avg_speed': 0} for side in sides}

    for api in target_flask_apis:
        try:
            response = requests.get(api)
            if response.status_code == 200:
                data = response.json()
                for side in sides:
                    aggregated_data[side]['vehicle_count'] += data[side]['vehicle_count']
                    aggregated_data[side]['vehicle_density'] += data[side]['vehicle_density']
                    aggregated_data[side]['priority'] += vehicle_priority.get(data[side]['vehicle_type'], 1)
                    aggregated_data[side]['avg_speed'] += data[side].get('avg_speed', 30)  # Default 30 km/h
        except requests.exceptions.RequestException:
            print(f"Failed to fetch data from {api}")
            continue
    
    return aggregated_data

# Function to calculate dynamic signal duration
def calculate_dynamic_signal_time(traffic_data, side):
    base_time = 5  # Minimum green light time
    max_time = 60  # Maximum green light time

    # Weighted calculation based on traffic conditions
    traffic_intensity = (
        traffic_data[side]['vehicle_count'] * traffic_data[side]['priority'] +
        traffic_data[side]['vehicle_density'] * 0.1 +
        (100 - traffic_data[side]['avg_speed']) * 0.2  # More waiting time if avg speed is low
    )

    # Normalize within range
    dynamic_time = min(max_time, max(base_time, int(traffic_intensity / 3)))
    
    return dynamic_time

# Function to update waiting time history
def update_waiting_time_history(signal_decision):
    for side in sides:
        if signal_decision[side]['signal'] == 'Green':
            waiting_time_history[side] = 0  # Reset if green
        else:
            waiting_time_history[side] += signal_decision[side]['duration']

# Function to make dynamic traffic signal decisions
def traffic_signal_decision(traffic_data):
    time_factor = get_time_factor()

    # Compute dynamic times for each side
    dynamic_durations = {side: calculate_dynamic_signal_time(traffic_data, side) * time_factor for side in sides}

    # CNN Model Prediction
    input_tensor = torch.tensor([[traffic_data[side]['vehicle_count'], traffic_data[side]['vehicle_density'], traffic_data[side]['priority'], traffic_data[side]['avg_speed']] for side in sides], dtype=torch.float32).unsqueeze(0).unsqueeze(0)
    output = model(input_tensor).detach().numpy().flatten()

    # Pick the side with the highest predicted traffic priority
    max_traffic_side = sides[output.argmax()]

    # Initialize signals as red
    signal_decision = {side: {'signal': 'Red', 'duration': 10} for side in sides}

    # Assign green signal dynamically
    signal_decision[max_traffic_side] = {'signal': 'Green', 'duration': int(dynamic_durations[max_traffic_side])}

    # Update history
    update_waiting_time_history(signal_decision)

    # Debugging output
    print(f"\nTraffic Data: {traffic_data}")
    print(f"Signal Decision: {signal_decision}\n")

    return signal_decision

@app.route('/')
def home():
    return "Welcome to the AI-Driven Junction Traffic Management System!"

@app.route('/get-traffic-signal', methods=['GET'])
def get_traffic_signal():
    traffic_data = fetch_traffic_data()
    signal_decision = traffic_signal_decision(traffic_data)
    return jsonify(signal_decision)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5009))
    app.run(host='0.0.0.0', port=port, debug=True)
