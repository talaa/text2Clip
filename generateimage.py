from together import Together
from dotenv import load_dotenv
import os
import requests



# Load environment variables from .env file
load_dotenv()


# Set your API key securely
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
client = Together(api_key=TOGETHER_API_KEY)


def generate_image(prompt, output_filename,output_dir="images"):
    
    os.makedirs(output_dir, exist_ok=True)

    response = client.images.generate(
        prompt=prompt,
        model="black-forest-labs/FLUX.1-schnell-Free",
        steps=3,
        n=1,
        height=1024,
        width=1024,
        seed=131346467979,
        guidance_scale=6,
        

    )
    image_url=(response.data[0].url)  # Print the base64-encoded image data
    # Ensure the 'images' directory exists
    images_dir = output_dir

    # Save image
    try:
        image_url = response.data[0].url  # Get the image URL from the response
        #print(f"Downloading image from: {image_url}")  # Debugging: Print the URL

        # Download the image from the URL
        response_image = requests.get(image_url)
        
        # Check if the download was successful
        if response_image.status_code == 200:
            filename = os.path.join(images_dir, output_filename+".png")
            with open(filename, "wb") as f:
                f.write(response_image.content)  # Write the binary content of the image
            print(f"Image saved to {filename}")
        else:
            print(f"Failed to download image. Status code: {response_image.status_code}")
    except AttributeError:
        print("Error: Response structure might have changed. Check the API response format.")
        print("Full response:", response)

