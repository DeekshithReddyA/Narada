import tkinter as tk
import vlc
import requests
import json
import os
import time
from threading import Thread
import logging

class VideoPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("Advertisement Display")
        
        # Make it fullscreen
        self.root.attributes('-fullscreen', True)
        
        # Create frame for video display
        self.frame = tk.Frame(root, bg='black')
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # Initialize VLC
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        
        # Set up display
        if os.name == "nt":
            self.player.set_hwnd(self.frame.winfo_id())
        else:
            self.player.set_xwindow(self.frame.winfo_id())
        
        # Video tracking
        self.current_ad = None
        self.current_video_path = None
        
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
        
        # Set up video end event handler for looping
        events = self.player.event_manager()
        events.event_attach(vlc.EventType.MediaPlayerEndReached, self.on_video_end)
        
        # Start location thread
        self.location_thread = Thread(target=self.location_update_loop, daemon=True)
        self.location_thread.start()
        
        # Bind escape key
        self.root.bind('<Escape>', lambda e: self.cleanup_and_exit())

    def on_video_end(self, event):
        """Simply restart the video when it ends"""
        self.player.set_position(0)  # Go back to start
        self.player.play()  # Play again

    def play_video(self, video_path):
        """Play a video"""
        if video_path != self.current_video_path:
            self.player.stop()
            media = self.instance.media_new(video_path)
            self.player.set_media(media)
            self.current_video_path = video_path
            self.player.play()

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
        while True:
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
        self.player.stop()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = VideoPlayer(root)
    root.mainloop()

if __name__ == "__main__":
    main()