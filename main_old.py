from flask import Flask, request, jsonify, send_file
from text2speech import text2speech
from scenecreator import createscenes
from generateimage import generate_image
from createvideo import create_video
import json
import os

# Initialize Flask app
app = Flask(__name__)

# Ensure output directories exist
os.makedirs("Audio", exist_ok=True)
os.makedirs("images", exist_ok=True)

#create the scenes with LLMs as json array
topic="What is the meaning of life ?"
num_of_scenes=2
scenes_array=[]

@app.route('/createscenes', methods=['POST'])
def createscenes():
    #start the process
    scenes=createscenes(topic,num_of_scenes)
    scenes = scenes.strip("```json\n").strip()
    # Parse the JSON string into a Python dictionary
    data = json.loads(scenes)

    # Extract the 'scenes' array
    scenes_array = data.get("scenes", [])
    return scenes_array


# Iterate over the scenes array and process each scene
@app.route('/process_scenes', methods=['POST'])
def process_scenes():
    for index, scene in enumerate(scenes_array):
        # Extract image_prompt and text
        image_prompt = scene.get("image_prompt", "")
        text = scene.get("text", "")

        # Generate a unique identifier for the scene (e.g., "scene0", "scene1", ...)
        scene_id = f"scene{index}"

        # Pass image_prompt to generate_image function
        generate_image(image_prompt, scene_id)

        # Pass text to text2speech function
        text2speech(text, scene_id)

#Create the Video 
@app.route('/create_video', methods=['POST'])
def create_video():
    # Call the create_video function to generate the final video
    create_video()

    # Return a success message or the path to the generated video
    return jsonify({"message": "Video created successfully", "video_path": "output_movie.mp4"})



@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint."""
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)