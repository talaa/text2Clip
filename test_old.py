import requests

base_url = "http://localhost:5000"

# Health check
print(requests.get(f"{base_url}/health").json())

# Generate scenes
response = requests.post(f"{base_url}/createscenes", json={"topic": "Exploring the universe", "num_scenes": 3})
scenes = response.json()["scenes"]
print("Scenes:", scenes)

# Process scenes
response = requests.post(f"{base_url}/process_scenes", json={"scenes": scenes})
print(response.json())

# Get video
response = requests.post(f"{base_url}/create_video")
with open("output_movie.mp4", "wb") as f:
    f.write(response.content)
print("Video saved as output_movie.mp4")