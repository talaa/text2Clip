from flask import Flask, request, jsonify, send_file
from text2speech import text2speech
from scenecreator import createscenes as create_scenes
from generateimage import generate_image
from createvideo import create_video
import json
import os
import shutil
import uuid
from dotenv import load_dotenv

# Initialize Flask app
app = Flask(__name__)

# Load environment variables
load_dotenv()

# Base directory for temporary files
BASE_TEMP_DIR = "temp"

# Ensure base temp directory exists
os.makedirs(BASE_TEMP_DIR, exist_ok=True)

@app.route('/generate_video', methods=['POST'])
def generate_video():
    try:
        # Get user input
        data = request.get_json()
        if not data or "topic" not in data or "num_scenes" not in data:
            return jsonify({"error": "Missing topic or num_scenes"}), 400
        
        topic = data["topic"]
        num_scenes = data["num_scenes"]
        
        if not isinstance(num_scenes, int) or num_scenes <= 0:
            return jsonify({"error": "num_scenes must be a positive integer"}), 400

        # Create a unique directory for this request
        request_id = str(uuid.uuid4())
        temp_dir = os.path.join(BASE_TEMP_DIR, request_id)
        audio_dir = os.path.join(temp_dir, "Audio")
        images_dir = os.path.join(temp_dir, "images")
        os.makedirs(audio_dir, exist_ok=True)
        os.makedirs(images_dir, exist_ok=True)

        # Step 1: Generate scenes
        scenes = create_scenes(topic, num_scenes)
        scenes = scenes.strip("```json\n").strip()
        scenes_data = json.loads(scenes)
        scenes_array = scenes_data.get("scenes", [])
        
        if not scenes_array:
            shutil.rmtree(temp_dir)  # Clean up on failure
            return jsonify({"error": "No scenes generated"}), 500

        # Step 2: Process scenes (generate images and audio)
        for index, scene in enumerate(scenes_array):
            image_prompt = scene.get("image_prompt", "")
            text = scene.get("text", "")
            scene_id = f"scene{index}"
            
            # Update generate_image and text2speech to use custom directories
            generate_image(image_prompt, scene_id, output_dir=images_dir)
            text2speech(text, scene_id, output_dir=audio_dir)

        # Step 3: Create video
        output_file = os.path.join(temp_dir, "output_movie.mp4")
        create_video(audio_dir=audio_dir, images_dir=images_dir, output_file=output_file)

        if not os.path.exists(output_file):
            shutil.rmtree(temp_dir)  # Clean up on failure
            return jsonify({"error": "Video creation failed"}), 500

        # Step 4: Send video and clean up
        response = send_file(output_file, mimetype='video/mp4', as_attachment=True, download_name="output_movie.mp4")
        shutil.rmtree(temp_dir)  # Clean up after sending
        return response

    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON format in scenes"}), 500
    except Exception as e:
        # Attempt to clean up if temp_dir exists
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)