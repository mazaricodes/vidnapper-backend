#!/usr/bin/env bash
# exit on error
set -o errexit

# Install our python libraries
pip install -r requirements.txt

# Download and install a static build of FFmpeg
FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
echo "Downloading and installing FFmpeg..."
curl -sL ${FFMPEG_URL} | tar xJ --strip-components=1 -C /usr/local/bin/
echo "FFmpeg setup complete."