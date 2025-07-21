# main.py
# To run this:
# 1. Install dependencies: pip install fastapi uvicorn yt-dlp
# 2. Make sure ffmpeg.exe is in the same folder as this file.
# 3. Run the server: python -m uvicorn main:app --reload --host 0.0.0.0

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from starlette.background import BackgroundTask # Import BackgroundTask
import yt_dlp
import re
import os
import uuid # To create unique filenames

# --- Pydantic Model for Request Body ---
class VideoLinkRequest(BaseModel):
    url: HttpUrl

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Video Downloader API",
    description="An API to get direct download links for videos from various platforms.",
    version="2.3.0", # Version updated for background task fix
)

TEMP_DIR = "temp_videos"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# --- API Endpoint ---
@app.post("/download-video-file/")
async def download_video_file(request: VideoLinkRequest):
    """
    Downloads the video file to the server, merges it, and sends the file back.
    """
    video_url = str(request.url)
    
    # Generate a unique filename to avoid conflicts
    unique_id = str(uuid.uuid4())
    output_template = os.path.join(TEMP_DIR, f"{unique_id}.%(ext)s")
    
    # --- New yt-dlp options to download and merge the file ---
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_template,
        'merge_output_format': 'mp4',
        'ffmpeg_location': os.path.dirname(os.path.abspath(__file__)),
        # 'cookiesfrombrowser': ('chrome',), 
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
    }

    try:
        # Use yt-dlp to download and merge the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            error_code = ydl.download([video_url])
            if error_code != 0:
                raise Exception("yt-dlp failed to download the video.")

        # Find the downloaded file
        final_filepath = os.path.join(TEMP_DIR, f"{unique_id}.mp4")
        
        if not os.path.exists(final_filepath):
            raise HTTPException(status_code=500, detail="Could not find the downloaded file on the server.")

        # --- FIX ---
        # Use a proper BackgroundTask to delete the file AFTER the response is sent.
        cleanup_task = BackgroundTask(os.remove, path=final_filepath)

        # Return the file directly to the app
        return FileResponse(
            path=final_filepath, 
            media_type='video/mp4', 
            filename=f"downloaded_video.mp4",
            background=cleanup_task # Use the cleanup task
        )
            
    except Exception as e:
        print(f"Error during download/merge: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred on the server.")


# --- Root Endpoint for Health Check ---
@app.get("/")
def read_root():
    """A simple endpoint to check if the API is running."""
    return {"status": "API is running"}
