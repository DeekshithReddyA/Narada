from flask import Flask, request, jsonify
from math import radians, sin, cos, sqrt, atan2
import json
import pynmea2  # For parsing NMEA GPS data

app = Flask(__name__)

# Example client data - in practice, this would come from a database
CLIENTS = [
    {
        "id": 1,
        "name": "SVM Grand",
        "type": "restaurant and Hotel",
        "location": {"latitude": 17.391178050899487 , "longitude": 78.55905092531569},  
        "radius": 5.0  # km
    },
    {
        "id": 2,
        "name": "Sharath City Capital Mall",
        "type": "Mall",
        "location": {"latitude": 17.458452306695207,  "longitude": 78.36314238570006},
        "radius": 5.0
    },
    {
        "id": 3,
        "name": "Rajiv Gandhi Internation Airport",
        "type": "Airport",
        "location": {"latitude": 17.24520257711281, "longitude":  78.42957533889812},
        "radius": 5.0
    }
]

def parse_gps_data(nmea_sentence):
    """
    Parse NMEA GPS data from NEO-6M module
    Expected format: $GPRMC or $GPGGA sentence
    """
    try:
        msg = pynmea2.parse(nmea_sentence)
        if isinstance(msg, (pynmea2.GGA, pynmea2.RMC)):
            if hasattr(msg, 'latitude') and hasattr(msg, 'longitude'):
                return {
                    "latitude": msg.latitude,
                    "longitude": msg.longitude,
                    "timestamp": msg.timestamp.isoformat() if hasattr(msg, 'timestamp') else None
                }
    except:
        return None
    return None

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two points using Haversine formula
    Returns distance in kilometers
    """
    R = 6371  # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c

    return distance

def find_nearest_client(vehicle_location):
    """
    Find the nearest client within radius
    Returns client info or None if no client is within radius
    """
    nearest_client = None
    min_distance = float('inf')

    for client in CLIENTS:
        distance = calculate_distance(
            vehicle_location["latitude"],
            vehicle_location["longitude"],
            client["location"]["latitude"],
            client["location"]["longitude"]
        )

        if distance <= client["radius"] or distance < min_distance:
            min_distance = distance
            nearest_client = {
                "client_id": client["id"],
                "client_name": client["name"],
                "client_type": client["type"],
                "distance": round(distance, 2)
            }

    return nearest_client

@app.route('/update-location', methods=['POST'])
def update_location():
    """
    Endpoint to receive vehicle location updates
    Expected POST data: {
        "vehicle_id": "string",
        "gps_data": "NMEA sentence string"
    }
    """
    data = request.get_json()
    
    if not data or 'vehicle_id' not in data or 'gps_data' not in data:
        return jsonify({"error": "Missing required data"}), 400

    # Parse GPS data
    location_data = parse_gps_data(data['gps_data'])
    if not location_data:
        return jsonify({"error": "Invalid GPS data"}), 400

    # Find nearest client
    nearest_client = find_nearest_client(location_data)

    response = {
        "vehicle_id": data["vehicle_id"],
        "timestamp": location_data["timestamp"],
        "location": {
            "latitude": location_data["latitude"],
            "longitude": location_data["longitude"]
        },
        "nearest_client": nearest_client
    }

    return jsonify(response)

@app.route('/clients', methods=['GET'])
def get_clients():
    """Endpoint to retrieve all client locations"""
    return jsonify(CLIENTS)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)