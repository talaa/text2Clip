from flask import Flask, request, jsonify, send_file
from flask_cors import CORS  # Import CORS
from text2speech import text2speech
from scenecreator import createscenes as create_scenes
from generateimage import generate_image
from createvideo import create_video
import json
import os
import shutil
import uuid
import threading
import time
import logging
import io
from dotenv import load_dotenv
import psutil

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

load_dotenv()
BASE_TEMP_DIR = "temp"
os.makedirs(BASE_TEMP_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s:%(name)s: %(message)s',
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def safe_rmtree(path, retries=3, delay=0.5):
    for attempt in range(retries):
        try:
            shutil.rmtree(path)
            logger.debug(f"Successfully deleted {path}")
            return True
        except PermissionError as e:
            logger.warning(f"Attempt {attempt + 1}/{retries} failed: {e}")
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
                logger.error(f"Could not delete {path} after {retries} attempts")
                return False
    return True

def cleanup_old_temp_dirs(max_age_hours=24):
    now = time.time()
    deleted = 0
    for folder in os.listdir(BASE_TEMP_DIR):
        path = os.path.join(BASE_TEMP_DIR, folder)
        if os.path.isdir(path):
            creation_time = os.path.getctime(path)
            age_hours = (now - creation_time) / 3600
            if age_hours > max_age_hours:
                logger.debug(f"Cleaning up old directory: {path}")
                if safe_rmtree(path):
                    deleted += 1
    return deleted

def update_status(task_dir, status, output_file=None):
    status_file = os.path.join(task_dir, "status.json")
    data = {"status": status}
    if output_file:
        data["output_file"] = output_file
    with open(status_file, 'w') as f:
        json.dump(data, f)

def generate_video_async(task_id, topic, num_scenes):
    task_dir = os.path.join(BASE_TEMP_DIR, task_id)
    audio_dir = os.path.join(task_dir, "Audio")
    images_dir = os.path.join(task_dir, "images")
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)
    logger.debug(f"Task {task_id} started in {task_dir}")
    logger.debug(f"Initial memory usage: {get_memory_usage()}")

    try:
        update_status(task_dir, "Generating scenes")
        scenes = create_scenes(topic, num_scenes)
        logger.debug(f"Memory usage after scene generation: {get_memory_usage()}")

        scenes = scenes.strip("```json\n").strip()
        scenes_data = json.loads(scenes)
        scenes_array = scenes_data.get("scenes", [])
        if not scenes_array:
            update_status(task_dir, "Error: No scenes generated")
            return

        update_status(task_dir, "Processing scenes")
        for index, scene in enumerate(scenes_array):
            image_prompt = scene.get("image_prompt", "")
            text = scene.get("text", "")
            scene_id = f"scene{index}"
            generate_image(image_prompt, scene_id, output_dir=images_dir)
            logger.debug(f"Memory usage after generating image {scene_id}: {get_memory_usage()}")
            text2speech(text, scene_id, output_dir=audio_dir)
            logger.debug(f"Memory usage after generating audio {scene_id}: {get_memory_usage()}")

        update_status(task_dir, "Creating video")
        output_file = os.path.join(task_dir, "output_movie.mp4")
        create_video(audio_dir=audio_dir, images_dir=images_dir, output_file=output_file, scenes_array=scenes_array)
        logger.debug(f"Memory usage after video creation: {get_memory_usage()}")

        if not os.path.exists(output_file):
            update_status(task_dir, "Error: Video creation failed")
            return

        update_status(task_dir, "Done", output_file=output_file)

    except Exception as e:
        update_status(task_dir, f"Error: {str(e)}")
        logger.error(f"Task {task_id} failed: {e}")

def get_memory_usage():
    """Returns the memory usage of the current process in MB."""
    process = psutil.Process()
    memory_info = process.memory_info()
    return {
        "rss": memory_info.rss / (1024 * 1024),  # Resident Set Size in MB
        "vms": memory_info.vms / (1024 * 1024),  # Virtual Memory Size in MB
        "percent": psutil.virtual_memory().percent  # System-wide memory usage percentage
    }

@app.route('/generate_clip', methods=['POST'])
def start_generate_video():
    data = request.get_json()
    if not data or "topic" not in data or "num_scenes" not in data:
        return jsonify({"error": "Missing topic or num_scenes"}), 400
    
    topic = data["topic"]
    num_scenes = data["num_scenes"]
    
    if not isinstance(num_scenes, int) or num_scenes <= 0:
        return jsonify({"error": "num_scenes must be a positive integer"}), 400
    if num_scenes > 6:
        return jsonify({"error": "num_scenes cannot exceed 6"}), 400

    task_id = str(uuid.uuid4())
    os.makedirs(os.path.join(BASE_TEMP_DIR, task_id), exist_ok=True)
    update_status(os.path.join(BASE_TEMP_DIR, task_id), "Queued")
    threading.Thread(target=generate_video_async, args=(task_id, topic, num_scenes)).start()
    return jsonify({"task_id": task_id}), 202

@app.route('/progress/<task_id>', methods=['GET'])
def get_progress(task_id):
    task_dir = os.path.join(BASE_TEMP_DIR, task_id)
    status_file = os.path.join(task_dir, "status.json")
    if not os.path.exists(status_file):
        return jsonify({"state": "PENDING", "status": "Task not found or queued"}), 404
    
    with open(status_file, 'r') as f:
        status_data = json.load(f)
    
    state = "PROGRESS" if status_data["status"].startswith("Error") or status_data["status"] == "Done" else "PROGRESS"
    if status_data["status"].startswith("Error"):
        state = "FAILURE"
    elif status_data["status"] == "Done":
        state = "SUCCESS"
    
    response = {"state": state, "status": status_data["status"]}
    if state == "SUCCESS":
        response["download_url"] = f"/download/{task_id}"
    return jsonify(response)

@app.route('/download/<task_id>', methods=['GET'])
def download_video(task_id):
    task_dir = os.path.join(BASE_TEMP_DIR, task_id)
    status_file = os.path.join(task_dir, "status.json")
    if not os.path.exists(status_file):
        return jsonify({"error": "Task not found"}), 404
    
    with open(status_file, 'r') as f:
        status_data = json.load(f)
    
    if status_data["status"] != "Done":
        return jsonify({"error": "Task not completed or failed"}), 400
    
    output_file = status_data["output_file"]
    if not os.path.exists(output_file):
        return jsonify({"error": "Video file not found"}), 500

    with open(output_file, 'rb') as f:
        video_data = io.BytesIO(f.read())
    response = send_file(
        video_data,
        mimetype='video/mp4',
        as_attachment=True,
        download_name="output_movie.mp4"
    )
    
    if not safe_rmtree(task_dir):
        logger.info(f"Deferred cleanup for {task_dir}")
    return response

@app.route('/cleanup', methods=['POST'])
def manual_cleanup():
    deleted = cleanup_old_temp_dirs()
    return jsonify({"message": f"Cleaned up {deleted} old temporary directories"}), 200

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/memory', methods=['GET'])
def memory_usage():
    memory = get_memory_usage()
    return jsonify({
        "rss_mb": memory["rss"],
        "vms_mb": memory["vms"],
        "system_memory_percent": memory["percent"]
    }), 200

@app.route('/delete_temp/<directory_name>', methods=['DELETE'])
def delete_temp_directory(directory_name):
    """
    Deletes a specified directory in the temp folder.
    """
    task_dir = os.path.join(BASE_TEMP_DIR, directory_name)
    if not os.path.exists(task_dir):
        return jsonify({"error": "Directory not found"}), 404

    if not os.path.isdir(task_dir):
        return jsonify({"error": "Specified path is not a directory"}), 400

    if safe_rmtree(task_dir):
        return jsonify({"message": f"Successfully deleted {directory_name}"}), 200
    else:
        return jsonify({"error": f"Failed to delete {directory_name}"}), 500

if __name__ == '__main__':
    cleanup_old_temp_dirs()
    app.run(host='0.0.0.0', port=5000, debug=True)