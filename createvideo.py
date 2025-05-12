from moviepy import *
import os




def create_video(audio_dir="Audio", images_dir="images", output_file="output_movie.mp4",scenes_array=None):
    # Get the list of audio files (ensure sorting is correct)
    scene_files = sorted([f for f in os.listdir(audio_dir) if f.endswith(".mp3")])
    #print(scenes_array)
    # Create a list to hold all video clips
    video_clips = []

    # Loop through each scene and create a video clip
    for scene_file in scene_files:
        scene_name = os.path.splitext(scene_file)[0]  # Remove .mp3 extension
        
        image_path = os.path.join(images_dir, f"{scene_name}.png")
        audio_path = os.path.join(audio_dir, scene_file)

        # Ensure the image file exists
        if not os.path.exists(image_path):
            print(f"Warning: Image file {image_path} not found. Skipping this scene.")
            continue

        # Load the audio file
        try:
            audio_clip = AudioFileClip(audio_path)
        except Exception as e:
            print(f"Error loading audio {audio_path}: {e}")
            continue

        # Create an ImageClip with the same duration as the audio
        image_clip = ImageClip(image_path, duration=audio_clip.duration)
        
        # Create a TextClip for the summary
        index=int(scene_name.replace("scene", "")) if scene_name.startswith("scene") else 0
        summary_text = scenes_array[index].get("summary", "") if scenes_array else ""
        print("summary",summary_text)
        """
        text_clip = TextClip(
            text=summary_text,
            font="arial.ttf",
            font_size=72,
            color="#FFFFFF",
            bg_color="#0000BB",  # Semi-transparent dark background
            size=(image_clip.w, None),  # Match the width of the image
            method="caption",
            duration=audio_clip.duration,# Match the duration of the audio
            horizontal_align="center",
            vertical_align="center",
        )
        print("text clip created")
        """
        # Overlay the TextClip on the ImageClip
        #composite_clip = CompositeVideoClip([image_clip, text_clip])
        
        # Set the audio of the image clip to the loaded audio
        #video_clip = composite_clip.with_audio(audio_clip)
        video_clip = image_clip.set_audio(audio_clip)
        if video_clip.audio is None:
            print(f"Error: Audio not attached to {scene_name}")
        else:
            print(f"Audio attached to {scene_name}")

        # Add the video clip to the list
        video_clips.append(video_clip)

        # Close clips to free memory
        image_clip.close()
        text_clip.close()
        composite_clip.close()
        audio_clip.close()
        
    # Check if we have clips before concatenating
    if video_clips:
        # Concatenate all video clips into one final video
        final_video = concatenate_videoclips(video_clips)

        # Export the final video to a file
        #output_file = "output_movie.mp4"
        final_video.write_videofile(
            output_file, 
            fps=24, 
            codec="libx264", 
            audio_codec="mp3",
            audio=True
            
            )
        final_video.close()  # Explicitly close the video object
        print(f"Movie created successfully: {output_file}")
    else:
        print("No valid video clips created. Check your files.")
