import tkinter as tk
from PIL import Image, ImageTk
import cv2
import requests
import json
import os
import time
from threading import Thread
import logging
import numpy as np

class VideoPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("Advertisement Display")
        
        # Make it fullscreen
        self.root.attributes('-fullscreen', True)
        
        # Create canvas for video display
        self.canvas = tk.Canvas(root, bg='black')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Video tracking
        self.current_ad = None
        self.current_video_path = None
        self.cap = None
        self.is_playing = False
        
        # Basic logging
        logging.basicConfig(filename='ad_player.log', level=logging.INFO)
        
        # Config
        self.config = {
            'gps_file': '/media/deeks/New Volume/Projects/Neer/mytest/frontend/gps.txt',
            'backend_url': 'http://localhost:5000/update-location',
            'request_interval': 5,
            'video_base_path': '/media/deeks/New Volume/Projects/Neer/mytest/frontend/clients',
            'vehicle_id': 'CAB001'
        }
        
        # Start threads
        self.keep_running = True
        self.location_thread = Thread(target=self.location_update_loop, daemon=True)
        self.video_thread = Thread(target=self.play_loop, daemon=True)
        self.location_thread.start()
        self.video_thread.start()
        
        # Bind escape key
        self.root.bind('<Escape>', lambda e: self.cleanup_and_exit())

    def play_video(self, video_path):
        """Start playing a new video"""
        if video_path != self.current_video_path:
            if self.cap is not None:
                self.cap.release()
            
            self.cap = cv2.VideoCapture(video_path)
            self.current_video_path = video_path
            self.is_playing = True
            logging.info(f"Playing video: {video_path}")

    def play_loop(self):
        """Main video playback loop"""
        while self.keep_running:
            if self.is_playing and self.cap is not None:
                ret, frame = self.cap.read()
                
                if ret:
                    # Resize frame to fit screen
                    screen_width = self.root.winfo_width()
                    screen_height = self.root.winfo_height()
                    
                    frame = cv2.resize(frame, (screen_width, screen_height))
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Convert frame to PhotoImage
                    image = Image.fromarray(frame)
                    photo = ImageTk.PhotoImage(image=image)
                    
                    # Update canvas
                    self.canvas.delete("all")
                    self.canvas.create_image(0, 0, image=photo, anchor=tk.NW)
                    self.canvas.image = photo  # Keep a reference
                    
                else:
                    # Video ended, restart from beginning
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                
                # Control frame rate
                time.sleep(1/60)  # Limit to 30 FPS

    def send_location_update(self):
        """Send location update to backend"""
        try:
            with open(self.config['gps_file'], 'r') as file:
                gps_data = file.read().strip()
            
            payload = {
                "vehicle_id": self.config['vehicle_id'],
                "gps_data": gps_data
            }
            
            response = requests.post(
                self.config['backend_url'],
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('nearest_client'):
                    return data['nearest_client']['client_name']
            return None
            
        except Exception as e:
            logging.error(f"Error sending location update: {e}")
            return None

    def get_video_path(self, client_name):
        """Get video file path"""
        client_dir = os.path.join(self.config['video_base_path'], client_name)
        if not os.path.exists(client_dir):
            return None
            
        videos = [f for f in os.listdir(client_dir) if f.endswith('.mp4')]
        if not videos:
            return None
            
        return os.path.join(client_dir, videos[0])

    def location_update_loop(self):
        """Check for location updates"""
        while self.keep_running:
            try:
                new_ad = self.send_location_update()
                if new_ad and new_ad != self.current_ad:
                    video_path = self.get_video_path(new_ad)
                    if video_path:
                        self.current_ad = new_ad
                        self.play_video(video_path)
                time.sleep(self.config['request_interval'])
            except Exception as e:
                logging.error(f"Error in location update: {e}")
                time.sleep(self.config['request_interval'])

    def cleanup_and_exit(self):
        """Clean up and exit"""
        self.keep_running = False
        if self.cap is not None:
            self.cap.release()
        self.root.destroy()

def main():
    # Install required packages if not already installed
    try:
        import cv2
    except ImportError:
        print("Installing required packages...")
        os.system('pip install opencv-python pillow')
        import cv2

    root = tk.Tk()
    app = VideoPlayer(root)
    root.mainloop()

if __name__ == "__main__":
    main()