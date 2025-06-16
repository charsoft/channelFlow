import subprocess
import ffmpeg
import os

def create_vertical_clip(input_path: str, output_path: str, start_time: float, end_time: float):
    """
    Clips a video and crops it to a 9:16 aspect ratio using ffmpeg via subprocess.

    Args:
        input_path: Path to the input video file.
        output_path: Path where the output video will be saved.
        start_time: Start time of the clip in seconds.
        end_time: End time of the clip in seconds.
    """
    try:
        print(f"Clipping video from {start_time} to {end_time} and cropping to 9:16.")
        
        # Probe the video to get its dimensions
        probe = ffmpeg.probe(input_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        width = int(video_stream['width'])
        height = int(video_stream['height'])

        # Calculate dimensions for 9:16 aspect ratio, cropping from the center
        new_height = height
        new_width = int(height * 9 / 16)
        x_offset = int((width - new_width) / 2)
        crop_filter = f"crop={new_width}:{new_height}:{x_offset}:0"

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        duration = end_time - start_time
        cmd = [
            'ffmpeg',
            '-ss', str(start_time),
            '-i', input_path,
            '-t', str(duration),
            '-vf', crop_filter,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-ar', '44100',
            '-b:a', '192k',
            '-y', # Overwrite output file if it exists
            output_path
        ]
        
        print("Executing ffmpeg command:", " ".join(cmd))
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        print(f"Successfully created clip: {output_path}")
        return output_path

    except subprocess.CalledProcessError as e:
        print('ffmpeg error:', e.stderr)
        raise e
    except Exception as e:
        print('An error occurred:', str(e))
        raise e 