from flask import Flask, request, jsonify, send_file
from text2speech import text2speech
from scenecreator import createscenes as create_scenes  # Renamed to avoid conflict
from generateimage import generate_image
from createvideo import create_video
import json
import os
from dotenv import load_dotenv

# Initialize Flask app
app = Flask(__name__)

# Load environment variables
load_dotenv()

# Ensure output directories exist
os.makedirs("Audio", exist_ok=True)
os.makedirs("images", exist_ok=True)

#Defining Global Variables 


@app.route('/createscenes', methods=['POST'])
def generate_scenes():
    try:
        data = request.get_json()
        if not data or "topic" not in data or "num_scenes" not in data:
            return jsonify({"error": "Missing topic or num_scenes"}), 400
        
        topic = data["topic"]
        num_scenes = data["num_scenes"]
        
        if not isinstance(num_scenes, int) or num_scenes <= 0:
            return jsonify({"error": "num_scenes must be a positive integer"}), 400

        scenes = create_scenes(topic, num_scenes)
        scenes = scenes.strip("```json\n").strip()
        scenes_data = json.loads(scenes)
        scenes_array = scenes_data.get("scenes", [])
        
        if not scenes_array:
            return jsonify({"error": "No scenes generated"}), 500
        
        return jsonify({"scenes": scenes_array}), 200
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON format in scenes"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/process_scenes', methods=['POST'])
def process_scenes():
    try:
        data = request.get_json()
        scenes_array = data.get("scenes", [])
        
        if not scenes_array:
            return jsonify({"error": "No scenes provided"}), 400

        for index, scene in enumerate(scenes_array):
            image_prompt = scene.get("image_prompt", "")
            text = scene.get("text", "")
            scene_id = f"scene{index}"
            generate_image(image_prompt, scene_id)
            text2speech(text, scene_id)
        
        return jsonify({"message": "Scenes processed successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/create_video', methods=['POST'])
def generate_video():
    try:
        create_video()
        output_file = "output_movie.mp4"
        if os.path.exists(output_file):
            return send_file(output_file, mimetype='video/mp4', as_attachment=True, download_name="output_movie.mp4")
        else:
            return jsonify({"error": "Video creation failed"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)