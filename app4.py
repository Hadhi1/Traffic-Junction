from flask import Flask, jsonify
import random
import time
from flask_cors import CORS
import os

app = Flask(__name__)

# Enable CORS for all routes
CORS(app)

# Define the four sides of the intersection
sides = ['North', 'South', 'East', 'West']

# Define vehicle types and their priority levels
vehicle_priority = {
    'Car': 1,
    'Bus': 2,
    'Truck': 3,
    'Bike': 0.5
}

# Initialize waiting time history for each side
waiting_time_history = {side: 0 for side in sides}

# Function to adjust timing based on rush hours
def get_time_factor():
    current_hour = time.localtime().tm_hour
    return 1.5 if 7 <= current_hour <= 9 or 17 <= current_hour <= 19 else 1  # Rush hour factor

# Function to generate random traffic data
def generate_traffic_data():
    traffic_data = {}
    for side in sides:
        vehicle_count = random.randint(0, 50)  # Simulated vehicles
        vehicle_density = random.randint(0, 100)  # Density percentage
        vehicle_type = random.choice(list(vehicle_priority.keys()))  # Random vehicle type
        
        traffic_data[side] = {
            'vehicle_count': vehicle_count,
            'vehicle_density': vehicle_density,
            'vehicle_type': vehicle_type,
            'priority': vehicle_priority[vehicle_type]  
        }
    return traffic_data

# Function to dynamically determine signal durations
def calculate_dynamic_signal_time(traffic_data, side):
    base_time = 5  # Minimum signal time in seconds
    max_time = 60  # Maximum signal time in seconds

    # Weighted time calculation based on vehicle count, density, and priority
    traffic_intensity = (
        traffic_data[side]['vehicle_count'] * traffic_data[side]['priority'] +
        traffic_data[side]['vehicle_density'] * 0.1
    )
    
    # Normalize time within range
    dynamic_time = min(max_time, max(base_time, int(traffic_intensity / 2)))
    
    return dynamic_time

# Function to determine traffic signal decisions dynamically
def traffic_signal_decision(traffic_data):
    time_factor = get_time_factor()

    # Compute dynamic times for each side
    dynamic_durations = {side: calculate_dynamic_signal_time(traffic_data, side) * time_factor for side in sides}

    # Select the side with the highest priority based on weighted traffic
    max_traffic_side = max(dynamic_durations, key=lambda side: dynamic_durations[side] + waiting_time_history[side] / 10)

    # Initialize all signals to red
    signal_decision = {side: {'signal': 'Red', 'duration': 10} for side in sides}

    # Assign green signal to the selected side with dynamically computed time
    signal_decision[max_traffic_side] = {'signal': 'Green', 'duration': int(dynamic_durations[max_traffic_side])}

    # Update waiting time history
    update_waiting_time_history(signal_decision)

    # Print output for monitoring
    print(f"\nTraffic Data: {traffic_data}")
    print(f"Signal Decision: {signal_decision}\n")

    return signal_decision

# Function to update waiting time history
def update_waiting_time_history(signal_decision):
    for side in sides:
        if signal_decision[side]['signal'] == 'Red':
            waiting_time_history[side] += signal_decision[side]['duration']
        else:
            waiting_time_history[side] = 0  # Reset waiting time for green signal

@app.route('/')
def home():
    return "Welcome to the Intelligent Traffic Management System API!"

@app.route('/get-traffic-signal', methods=['GET'])
def get_traffic_signal():
    traffic_data = generate_traffic_data()
    signal_decision = traffic_signal_decision(traffic_data)
    return jsonify(signal_decision)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5003))  # Use environment variable or default to 5003
    app.run(host='0.0.0.0', port=port, debug=True)
