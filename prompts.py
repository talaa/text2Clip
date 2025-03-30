SCENE_GENERATION_PROMPT = """
You are a world-class scene generator. Given a topic and a number of scenes, 
generate a structured sequence in JSON format. Each scene must include:
- "image_prompt": A detailed visual description optimized for AI image generation.
- "text": A vivid narrative description.

Example Output:
{{
    "scenes": [
        {{
            "image_prompt": "A beautiful depiction of the first scene.",
            "text": "This is the first scene."
        }}
    ]
}}

Topic: {topic}
Number of Scenes: {num_scenes}
"""
