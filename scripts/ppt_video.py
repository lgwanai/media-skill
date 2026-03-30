import argparse
import json
import os
import subprocess
import requests

def download_image(url, output_path):
    print(f"Downloading image from {url}...")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Saved image to {output_path}")

def generate_scene_video(image_path, audio_path, output_video_path):
    print(f"Generating video for scene: {output_video_path}...")
    # Generate a 1920x1080 30fps video with aac audio
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", image_path, "-i", audio_path,
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black",
        "-c:v", "libx264", "-preset", "fast", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
        "-pix_fmt", "yuv420p", "-r", "30", "-shortest", output_video_path
    ]
    subprocess.run(cmd, check=True)
    print(f"Generated scene video: {output_video_path}")

def main():
    parser = argparse.ArgumentParser(description="Generate PPT-style video from scenes")
    parser.add_argument("--scenes", required=True, help="Path to JSON file containing scenes list")
    parser.add_argument("--voice", default="default", help="Voice to use for dubbing")
    parser.add_argument("--out", default="output/ppt_final_video.mp4", help="Output final video path")
    parser.add_argument("--temperature", default="0.1", help="Temperature for TTS emotion fluctuation")
    args = parser.parse_args()

    with open(args.scenes, 'r', encoding='utf-8') as f:
        scenes = json.load(f)

    os.makedirs("output", exist_ok=True)
    
    scene_videos = []
    
    for idx, scene in enumerate(scenes):
        print(f"\n--- Processing Scene {idx+1}/{len(scenes)} ---")
        img_url = scene.get("image_url")
        text = scene.get("text")
        
        if not img_url or not text:
            print(f"Warning: Scene {idx+1} is missing image_url or text. Skipping.")
            continue
            
        base_name = f"output/ppt_scene_{idx}"
        img_path = f"{base_name}_img.jpg"
        audio_path = f"{base_name}_audio.mp3"
        video_path = f"{base_name}_video.mp4"
        sub_video_path = f"{base_name}_sub.mp4"
        
        # 1. Download Image
        download_image(img_url, img_path)
        
        # 2. Dub Text
        print(f"Dubbing text: {text[:30]}...")
        dub_cmd = [
            "python", "scripts/dubbing.py", "dub",
            "--text", text, "--voice", args.voice, "--out", audio_path,
            "--temperature", args.temperature
        ]
        subprocess.run(dub_cmd, check=True)
        
        # 3. Create Scene Video
        generate_scene_video(img_path, audio_path, video_path)
        
        # 4. Add Subtitles
        print(f"Adding subtitles to scene {idx+1}...")
        sub_cmd = [
            "python", "scripts/subtitle.py", video_path, "--out", sub_video_path
        ]
        subprocess.run(sub_cmd, check=True)
        
        scene_videos.append(sub_video_path)
        
    print("\n--- Merging All Scenes ---")
    if not scene_videos:
        print("No valid scenes processed.")
        return
        
    concat_file = "output/concat.txt"
    with open(concat_file, "w", encoding="utf-8") as f:
        for vid in scene_videos:
            f.write(f"file '{os.path.abspath(vid)}'\n")
            
    final_out = os.path.abspath(args.out)
    merge_cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
        "-c", "copy", final_out
    ]
    subprocess.run(merge_cmd, check=True)
    print(f"\n🎉 Successfully generated PPT video: {final_out}")

if __name__ == "__main__":
    main()
