from flask import Flask, request, jsonify
from math import radians, sin, cos, sqrt, atan2
import json
import pynmea2
from datetime import datetime

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


def convert_nmea_to_decimal(nmea_value, direction):
    """
    Convert NMEA coordinate format to decimal degrees
    Example: convert_nmea_to_decimal("1724.2473", "N")
    """
    try:
        # Split into degrees and minutes
        if '.' in nmea_value:
            degrees = float(nmea_value[:nmea_value.index('.')-2])
            minutes = float(nmea_value[nmea_value.index('.')-2:])
        else:
            degrees = float(nmea_value[:-2])
            minutes = float(nmea_value[-2:])

        # Convert to decimal degrees
        decimal = degrees + (minutes / 60)
        
        # Apply direction
        if direction in ['S', 'W']:
            decimal = -decimal
            
        return round(decimal, 6)
    except Exception as e:
        print(f"Error converting coordinate: {str(e)}")
        return None

def parse_gpgga_manual(nmea_sentence):
    """
    Manually parse GPGGA sentence without relying on checksum validation
    """
    try:
        # Remove leading '$' if present
        if nmea_sentence.startswith('$'):
            nmea_sentence = nmea_sentence[1:]
            
        # Split the sentence into parts
        parts = nmea_sentence.split(',')
        
        # Remove checksum from last field
        if '*' in parts[-1]:
            parts[-1] = parts[-1].split('*')[0]
            
        if len(parts) < 15 or not parts[2] or not parts[4]:
            return None
            
        # Extract and convert coordinates
        latitude = convert_nmea_to_decimal(parts[2], parts[3])
        longitude = convert_nmea_to_decimal(parts[4], parts[5])
        
        if latitude is None or longitude is None:
            return None
            
        # Parse other fields
        timestamp = parts[1]
        quality = int(parts[6]) if parts[6] else 0
        satellites = int(parts[7]) if parts[7] else 0
        hdop = float(parts[8]) if parts[8] else 0.0
        altitude = float(parts[9]) if parts[9] else 0.0
        
        return {
            "latitude": latitude,
            "longitude": longitude,
            "altitude": altitude,
            "satellites": satellites,
            "hdop": hdop,
            "timestamp": datetime.strptime(timestamp, "%H%M%S").time().isoformat() if timestamp else None,
            "quality": quality
        }
    except Exception as e:
        print(f"Error in manual GPGGA parsing: {str(e)}")
        return None

def parse_gpgga(nmea_sentence):
    """
    Try parsing GPGGA sentence first with pynmea2, then fall back to manual parsing
    """
    try:
        # First try with pynmea2
        msg = pynmea2.parse(nmea_sentence)
        if isinstance(msg, pynmea2.GGA):
            latitude = msg.latitude
            if msg.lat_dir == 'S':
                latitude = -latitude
                
            longitude = msg.longitude
            if msg.lon_dir == 'W':
                longitude = -longitude
                
            return {
                "latitude": latitude,
                "longitude": longitude,
                "altitude": msg.altitude,
                "satellites": msg.num_sats,
                "hdop": msg.horizontal_dil,
                "timestamp": msg.timestamp.isoformat() if hasattr(msg, 'timestamp') else None,
                "quality": msg.gps_qual
            }
    except Exception as e:
        print(f"pynmea2 parsing failed, trying manual parse: {str(e)}")
        
    # Fall back to manual parsing
    return parse_gpgga_manual(nmea_sentence)

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
    """
    data = request.get_json()
    
    if not data or 'vehicle_id' not in data or 'gps_data' not in data:
        return jsonify({"error": "Missing required data"}), 400

    # Parse GPS data
    location_data = parse_gpgga(data['gps_data'])
    if not location_data:
        return jsonify({"error": "Invalid GPS data or parsing failed"}), 400

    # Find nearest client
    nearest_client = find_nearest_client(location_data)

    response = {
        "vehicle_id": data["vehicle_id"],
        "timestamp": location_data["timestamp"],
        "location": {
            "latitude": location_data["latitude"],
            "longitude": location_data["longitude"],
            "altitude": location_data["altitude"],
            "satellites": location_data["satellites"],
            "hdop": location_data["hdop"],
            "quality": location_data["quality"]
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