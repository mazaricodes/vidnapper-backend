# main.py (Definitive for Render/HF deployment)

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from starlette.background import BackgroundTask
import yt_dlp
import os
import uuid # To create unique filenames
import json # For better error logging

# --- Pydantic Model for Request Body ---
class VideoLinkRequest(BaseModel):
    url: HttpUrl

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Vidnapper API",
    description="An API to download and serve videos from various platforms.",
    version="6.0.0", # Version with Cookies Fix
)

# --- THIS IS THE FIX ---
# Use the /tmp directory, which is a standard writable folder on servers like Render.
TEMP_DIR = "/tmp/temp_videos"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# --- API Endpoint ---
@app.post("/download-video-file/")
async def download_video_file(request: VideoLinkRequest):
    """
    Downloads the video file to the server, merges it, and sends the file back.
    """
    video_url = str(request.url)
    
    unique_id = str(uuid.uuid4())
    output_template = os.path.join(TEMP_DIR, f"{unique_id}.%(ext)s")
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_template,
        'merge_output_format': 'mp4',
        'dns_servers': ['8.8.8.8'],
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        },
        'ignoreerrors': True,
    }

    # Check if a cookies.txt file exists in the project directory.
    # If it does, use it for authentication.
    cookies_path = 'cookies.txt'
    if os.path.exists(cookies_path):
        print("--- INFO: Found cookies.txt, using for authentication. ---")
        ydl_opts['cookies'] = cookies_path

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
            
            if info_dict is None:
                raise yt_dlp.utils.DownloadError("yt-dlp could not extract information. The video might be private, deleted, or require a login.")

            error_code = ydl.download([video_url])
            if error_code != 0:
                raise Exception("yt-dlp failed during the download process.")

        final_filepath = os.path.join(TEMP_DIR, f"{unique_id}.mp4")
        
        if not os.path.exists(final_filepath):
            raise HTTPException(status_code=500, detail="Downloaded file not found on the server.")

        cleanup_task = BackgroundTask(os.remove, path=final_filepath)

        return FileResponse(
            path=final_filepath, 
            media_type='video/mp4', 
            filename=f"downloaded_video.mp4",
            background=cleanup_task
        )
            
    except yt_dlp.utils.DownloadError as e:
        print(f"yt-dlp DownloadError: {e}")
        error_message = str(e).lower()
        if "private" in error_message or "login is required" in error_message or "sign in" in error_message:
             raise HTTPException(status_code=403, detail="This video is private or requires a login to download.")
        if "unavailable" in error_message:
             raise HTTPException(status_code=404, detail="This video is unavailable or has been deleted.")
        raise HTTPException(status_code=500, detail="Failed to process the video link.")
    except Exception as e:
        print(f"Error during download/merge: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred on the server.")


# --- Root Endpoint for Health Check ---
@app.get("/")
def read_root():
    """A simple endpoint to check if the API is running."""
    return {"status": "API is running"}
