# main.py
# To run this:
# 1. Install dependencies: pip install fastapi uvicorn yt-dlp
# 2. For local testing, ensure ffmpeg is installed and in your system's PATH.
# 3. Run the server: python -m uvicorn main:app --reload --host 0.0.0.0

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from starlette.background import BackgroundTask
import yt_dlp
import os
import uuid # To create unique filenames

# --- Pydantic Model for Request Body ---
class VideoLinkRequest(BaseModel):
    url: HttpUrl

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Vidnapper API",
    description="An API to download and serve videos from various platforms.",
    version="3.0.0", # Version for Render deployment
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
    
    unique_id = str(uuid.uuid4())
    output_template = os.path.join(TEMP_DIR, f"{unique_id}.%(ext)s")
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_template,
        'merge_output_format': 'mp4',
        # 'cookiesfrombrowser': ('chrome',), # Disabled for server compatibility
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            error_code = ydl.download([video_url])
            if error_code != 0:
                raise Exception("yt-dlp failed to download the video.")

        final_filepath = os.path.join(TEMP_DIR, f"{unique_id}.mp4")
        
        if not os.path.exists(final_filepath):
            raise HTTPException(status_code=500, detail="Could not find the downloaded file on the server.")

        cleanup_task = BackgroundTask(os.remove, path=final_filepath)

        return FileResponse(
            path=final_filepath, 
            media_type='video/mp4', 
            filename=f"downloaded_video.mp4",
            background=cleanup_task
        )
            
    except Exception as e:
        print(f"Error during download/merge: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred on the server.")


# --- Root Endpoint for Health Check ---
@app.get("/")
def read_root():
    """A simple endpoint to check if the API is running."""
    return {"status": "API is running"}
