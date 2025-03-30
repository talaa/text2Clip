from flask import Flask, request, jsonify, send_file
from text2speech import text2speech
from scenecreator import createscenes as create_scenes
from generateimage import generate_image
from createvideo import create_video
import json
import os
import shutil
import uuid
import time
import logging
import io
from dotenv import load_dotenv

# Initialize Flask app
app = Flask(__name__)

# Load environment variables
load_dotenv()

# Base directory for temporary files
BASE_TEMP_DIR = "temp"

# Ensure base temp directory exists
os.makedirs(BASE_TEMP_DIR, exist_ok=True)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def safe_rmtree(path, retries=3, delay=0.5):
    """Safely remove a directory with minimal retries."""
    for attempt in range(retries):
        try:
            shutil.rmtree(path)
            logger.debug(f"Successfully deleted {path}")
            return True
        except PermissionError as e:
            logger.warning(f"Attempt {attempt + 1}/{retries} failed to delete {path}: {e}")
            # Log which files are locked
            for root, dirs, files in os.walk(path, topdown=False):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        os.remove(file_path)
                    except PermissionError as pe:
                        logger.error(f"File locked: {file_path} - {pe}")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                logger.error(f"Could not delete {path} after {retries} attempts; will defer cleanup")
                return False
    return True

def cleanup_old_temp_dirs(max_age_hours=24):
    """Clean up old temp directories older than max_age_hours."""
    now = time.time()
    for folder in os.listdir(BASE_TEMP_DIR):
        path = os.path.join(BASE_TEMP_DIR, folder)
        if os.path.isdir(path):
            creation_time = os.path.getctime(path)
            age_hours = (now - creation_time) / 3600
            if age_hours > max_age_hours:
                logger.debug(f"Cleaning up old directory: {path}")
                safe_rmtree(path)

@app.route('/generate_clip', methods=['POST'])
def generate_video():
    temp_dir = None
    output_file = None
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
        logger.debug(f"Created temp directory: {temp_dir}")

        # Step 1: Generate scenes
        scenes = create_scenes(topic, num_scenes)
        scenes = scenes.strip("```json\n").strip()
        scenes_data = json.loads(scenes)
        scenes_array = scenes_data.get("scenes", [])
        
        if not scenes_array:
            safe_rmtree(temp_dir)
            return jsonify({"error": "No scenes generated"}), 500

        # Step 2: Process scenes
        for index, scene in enumerate(scenes_array):
            image_prompt = scene.get("image_prompt", "")
            text = scene.get("text", "")
            scene_id = f"scene{index}"
            generate_image(image_prompt, scene_id, output_dir=images_dir)
            text2speech(text, scene_id, output_dir=audio_dir)

        # Step 3: Create video
        output_file = os.path.join(temp_dir, "output_movie.mp4")
        create_video(audio_dir=audio_dir, images_dir=images_dir, output_file=output_file)

        if not os.path.exists(output_file):
            safe_rmtree(temp_dir)
            return jsonify({"error": "Video creation failed"}), 500

        # Step 4: Send video using a file-like object
        with open(output_file, 'rb') as f:
            video_data = io.BytesIO(f.read())
        response = send_file(
            video_data,
            mimetype='video/mp4',
            as_attachment=True,
            download_name="output_movie.mp4"
        )

        # Step 5: Attempt immediate cleanup (minimal retries)
        logger.debug(f"Sent {output_file}; attempting cleanup")
        if not safe_rmtree(temp_dir):
            logger.info(f"Deferred cleanup for {temp_dir} to next startup")

        return response

    except json.JSONDecodeError:
        if temp_dir and os.path.exists(temp_dir):
            safe_rmtree(temp_dir)
        return jsonify({"error": "Invalid JSON format in scenes"}), 500
    except Exception as e:
        if temp_dir and os.path.exists(temp_dir):
            safe_rmtree(temp_dir)
        return jsonify({"error": str(e)}), 500
    finally:
        if temp_dir and os.path.exists(temp_dir):
            logger.debug(f"Final cleanup attempt for {temp_dir}")
            safe_rmtree(temp_dir)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    cleanup_old_temp_dirs()  # Clean up old folders on startup
    app.run(host='0.0.0.0', port=5000, debug=True)