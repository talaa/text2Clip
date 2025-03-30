from gtts import gTTS
import os



def text2speech(text,filename, lang='en',output_dir="Audio"):
    """
    Convert text to speech and save it as an audio file.

    :param text: The text to convert to speech.
    :param lang: The language in which to convert the text (default is English).
    :param filename: The name of the output audio file (default is 'output.mp3').
    """
    
    # Create a gTTS object
    tts = gTTS(text=text, lang=lang)

    # Save the audio file
    
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename+".mp3")
    tts.save(filepath)
    print(f"Audio saved as {filename}")
