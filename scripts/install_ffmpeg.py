import os
import zipfile
import urllib.request
import shutil
import sys

FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
INSTALL_DIR = r"D:\Projetos\lab_pro_poc"
FFMPEG_DIR_NAME = "ffmpeg"
TARGET_DIR = os.path.join(INSTALL_DIR, FFMPEG_DIR_NAME)

def install_ffmpeg():
    print(f"Downloading FFmpeg from {FFMPEG_URL}...")
    zip_path = os.path.join(INSTALL_DIR, "ffmpeg.zip")
    
    try:
        # User-Agent header is sometimes required
        opener = urllib.request.build_opener()
        opener.addheaders = [('User-agent', 'Mozilla/5.0')]
        urllib.request.install_opener(opener)
        
        urllib.request.urlretrieve(FFMPEG_URL, zip_path)
        print("Download complete.")
        
        print("Extracting...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Get the root folder name inside the zip
            root_folder = zip_ref.namelist()[0].split('/')[0]
            zip_ref.extractall(INSTALL_DIR)
            
        # Rename extracted folder to 'ffmpeg'
        extracted_path = os.path.join(INSTALL_DIR, root_folder)
        if os.path.exists(TARGET_DIR):
            shutil.rmtree(TARGET_DIR)
        os.rename(extracted_path, TARGET_DIR)
        
        print(f"FFmpeg installed to {TARGET_DIR}")
        
        # Verify bin
        bin_path = os.path.join(TARGET_DIR, "bin")
        if os.path.exists(os.path.join(bin_path, "ffmpeg.exe")):
            print("ffmpeg.exe found.")
        else:
            print("Error: ffmpeg.exe not found in expected bin path.")
            
        # Cleanup
        os.remove(zip_path)
        
    except Exception as e:
        print(f"Failed to install FFmpeg: {e}")
        sys.exit(1)

if __name__ == "__main__":
    install_ffmpeg()
