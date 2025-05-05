import cv2
from PIL import Image
import imageio
import os

image_extenstions = ['jpeg', 'png', 'bmp']

cwd = os.path.abspath(os.getcwd())
prefix = f'{cwd}/source'

def convert(input_file, frame_number=0):
    global prefix

    output_file = f"{prefix}/static/temp/media/{input_file.split('.')[0].split('/')[-1]}.jpeg"
    if input_file.lower().split('.')[-1] in image_extenstions:
        return input_file
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Error: File '{input_file}' not found.")

    # Handle GIFs using imageio
    if input_file.lower().endswith(".gif"):
        try:
            with imageio.get_reader(input_file) as gif_reader:
                num_frames = gif_reader.get_length()
                if frame_number >= num_frames:
                    frame_number = num_frames - 1  # Use last frame if out of range
                
                frame = gif_reader.get_data(frame_number)  # Read only one frame
                img = Image.fromarray(frame)  # Convert to PIL Image
        except Exception as e:
            print(f"Error reading GIF: {e}")
            return False
    else:
        cap = cv2.VideoCapture(input_file)

        if not cap.isOpened():
            print("Error: Cannot open video file. OpenCV may not support this format.")
            return False

        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)  # Set frame position
        ret, frame = cap.read()
        cap.release()

        if not ret:
            print(f"Error: Could not read frame {frame_number}.")
            return False

        # Convert BGR (OpenCV default) to RGB for correct colors
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame)

    # Save as uncompressed BMP
    try:
        if ((img.width>400)and(img.height>400)):
            img.resize((400,400))
        img.save(output_file, "JPEG")
        #print(f"Frame {frame_number} saved as {output_file}")
        return output_file
    except Exception as e:
        print(f"Error saving JPEG: {e}")
        return False
    
def add_overlay(input_file, data):
    icon_prefix = f'{prefix}\\static\\icons'
    rank_paths = {
        'None' : 'undefined.png',
        '0' : '0.png',
        '1' : '1.png',
        '2' : '2.png',
        '3' : '3.png',
        '4' : '4.png'
    }
    
    img = Image.open(input_file).convert("RGBA")
    path = f'{icon_prefix}\\{rank_paths[str(data["rank"])]}'
    overlay = Image.open(path).convert("RGBA")
    #resize overlay
    '''
    overlay_x = img.size[0]//4
    overlay_y = round((overlay_x//overlay.size[0])*overlay.size[1])
    new_size = (overlay_x, overlay_y)
    print(new_size)
    overlay.resize(new_size)
    '''
    #paste
    img.paste(overlay, (0, 0), overlay)
    img.save(input_file, "PNG")
    img.close()
    overlay.close()
    
'''     q   
if len(sys.argv) < 2:
    print("Usage: python script.py <video_file> [frame_number]")
else:
    file_path = sys.argv[1]
    frame_num = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    convert(file_path, frame_num)
'''   