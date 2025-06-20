import subprocess
import ffmpeg
import os

def create_vertical_clip(input_path: str, output_path: str, start_time: float, end_time: float, mask_path: str = None):
    """
    Clips a video, crops it to 9:16, and optionally overlays a mask.
    """
    try:
        print(f"Processing clip from {start_time} to {end_time}...")
        
        probe = ffmpeg.probe(input_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        width = int(video_stream['width'])
        height = int(video_stream['height'])

        new_height = height
        new_width = int(height * 9 / 16)
        x_offset = int((width - new_width) / 2)
        crop_filter = f"crop={new_width}:{new_height}:{x_offset}:0"

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        duration = end_time - start_time
        
        input_video = ffmpeg.input(input_path, ss=start_time, t=duration)
        processed_video = input_video.filter('vf', crop_filter)

        if mask_path and os.path.exists(mask_path):
            print(f"Applying mask: {mask_path}")
            mask_input = ffmpeg.input(mask_path)
            # Scale the cropped video to fit the standard 1080x1920 short format
            scaled_video = processed_video.filter('scale', 1080, 1920)
            # Overlay the mask
            final_video = ffmpeg.overlay(scaled_video, mask_input, x='0', y='0')
            args = final_video.output(
                output_path, 
                acodec='aac', 
                ar='44100', 
                b_a='192k', 
                vcodec='libx264'
            ).overwrite_output().get_args()
            cmd = ['ffmpeg'] + args
        else:
            final_video = processed_video
            args = final_video.output(
                output_path, 
                acodec='aac', 
                ar='44100', 
                b_a='192k', 
                vcodec='libx264'
            ).overwrite_output().get_args()
            cmd = ['ffmpeg'] + args

        print("Executing ffmpeg command:", " ".join(cmd))
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        print(f"Successfully created clip: {output_path}")
        return output_path

    except ffmpeg.Error as e:
        print('ffmpeg error:', e.stderr.decode() if e.stderr else 'Unknown ffmpeg error')
        raise e
    except Exception as e:
        print('An error occurred:', str(e))
        raise e 