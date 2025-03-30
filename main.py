from text2speech import text2speech
from scenecreator import createscenes
from generateimage import generate_image
from createvideo import create_video
import json



#create the scenes with LLMs as json array
topic="What is the meaning of life ?"
num_of_scenes=2

#start the process
scenes=createscenes(topic,num_of_scenes)
scenes = scenes.strip("```json\n").strip()
# Parse the JSON string into a Python dictionary
data = json.loads(scenes)

# Extract the 'scenes' array
scenes_array = data.get("scenes", [])


# Iterate over the scenes array and process each scene
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
create_video()
