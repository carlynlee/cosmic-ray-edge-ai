#!/usr/bin/env python3
"""
Script to extract and prepare images from hit-images-final.zip for clustering
"""
import os
import zipfile
import shutil
from pathlib import Path

def extract_images():
    """Extract images from hit-images-final.zip to /data/images"""
    
    # Define paths
    zip_path = "/workspace/hit-images-final.zip"
    extract_path = "/data/images"
    
    # Create extraction directory if it doesn't exist
    os.makedirs(extract_path, exist_ok=True)
    
    print(f"Extracting images from {zip_path} to {extract_path}")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        
        # Count extracted files
        extracted_files = []
        for root, dirs, files in os.walk(extract_path):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    extracted_files.append(os.path.join(root, file))
        
        print(f"Successfully extracted {len(extracted_files)} image files")
        
        # Create a simple index file
        index_file = os.path.join(extract_path, "image_index.txt")
        with open(index_file, 'w') as f:
            for file_path in extracted_files:
                f.write(f"{file_path}\n")
        
        print(f"Created image index at {index_file}")
        
    except Exception as e:
        print(f"Error extracting images: {e}")
        return False
    
    return True

def setup_directories():
    """Create necessary directories for the project"""
    
    directories = [
        "/data/models",
        "/data/exports", 
        "/data/processed",
        "/workspace/notebooks"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")

if __name__ == "__main__":
    print("Setting up CREDO image clustering environment...")
    
    # Create directories
    setup_directories()
    
    # Extract images if zip file exists
    if os.path.exists("/workspace/hit-images-final.zip"):
        extract_images()
    else:
        print("hit-images-final.zip not found in /workspace")
        print("Please ensure the zip file is available in the workspace")
    
    print("Setup complete!") 