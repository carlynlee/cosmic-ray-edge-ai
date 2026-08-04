#!/usr/bin/env python3
"""
Analyze device IDs from CREDO image files
Prepare for federated learning setup
"""

import os
import glob
import pandas as pd
from collections import Counter
import matplotlib.pyplot as plt
import json

def extract_device_ids():
    """Extract device IDs from image filenames"""
    images_dir = "/data/images"
    device_data = {}
    
    print("Analyzing device IDs from image files...")
    
    # Find all image files
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp']
    all_images = []
    
    for ext in image_extensions:
        all_images.extend(glob.glob(os.path.join(images_dir, '**', ext), recursive=True))
        all_images.extend(glob.glob(os.path.join(images_dir, '**', ext.upper()), recursive=True))
    
    print(f"Found {len(all_images)} total images")
    
    # Extract device IDs from filenames
    device_ids = []
    filename_patterns = []
    
    for img_path in all_images:
        filename = os.path.basename(img_path)
        
        # Try different patterns to extract device ID
        patterns = [
            filename.split('_')[0] if '_' in filename else None,
            filename.split('.')[0] if '.' in filename else None,
            filename[:8] if len(filename) >= 8 else None,  # First 8 characters
            filename[:6] if len(filename) >= 6 else None,  # First 6 characters
        ]
        
        for pattern in patterns:
            if pattern and pattern.isdigit():
                device_ids.append(pattern)
                filename_patterns.append({
                    'filename': filename,
                    'device_id': pattern,
                    'full_path': img_path
                })
                break
    
    print(f"Extracted {len(device_ids)} device IDs")
    
    # Analyze device ID distribution
    device_counter = Counter(device_ids)
    
    print("\nDevice ID Analysis:")
    print(f"Unique device IDs: {len(device_counter)}")
    print(f"Total images with device IDs: {len(device_ids)}")
    
    # Show top 10 devices by image count
    print("\nTop 10 devices by image count:")
    for device_id, count in device_counter.most_common(10):
        print(f"  Device {device_id}: {count} images")
    
    # Create detailed analysis
    analysis = {
        'total_images': len(all_images),
        'images_with_device_ids': len(device_ids),
        'unique_device_ids': len(device_counter),
        'device_distribution': dict(device_counter.most_common()),
        'filename_patterns': filename_patterns[:100]  # First 100 for analysis
    }
    
    # Save analysis
    analysis_file = "/data/exports/device_id_analysis.json"
    os.makedirs(os.path.dirname(analysis_file), exist_ok=True)
    
    with open(analysis_file, 'w') as f:
        json.dump(analysis, f, indent=2)
    
    print(f"\nAnalysis saved to {analysis_file}")
    
    # Create visualization
    plt.figure(figsize=(15, 10))
    
    # Plot 1: Device distribution (top 20)
    plt.subplot(2, 2, 1)
    top_devices = device_counter.most_common(20)
    device_names = [f"Device {d[0]}" for d in top_devices]
    device_counts = [d[1] for d in top_devices]
    
    plt.bar(range(len(device_names)), device_counts)
    plt.title('Top 20 Devices by Image Count')
    plt.xlabel('Device ID')
    plt.ylabel('Number of Images')
    plt.xticks(range(len(device_names)), device_names, rotation=45, ha='right')
    
    # Plot 2: Cumulative distribution
    plt.subplot(2, 2, 2)
    sorted_counts = sorted(device_counter.values(), reverse=True)
    cumulative = [sum(sorted_counts[:i+1]) for i in range(len(sorted_counts))]
    plt.plot(range(1, len(cumulative) + 1), cumulative)
    plt.title('Cumulative Image Distribution')
    plt.xlabel('Number of Devices')
    plt.ylabel('Cumulative Images')
    plt.grid(True, alpha=0.3)
    
    # Plot 3: Histogram of image counts per device
    plt.subplot(2, 2, 3)
    plt.hist(list(device_counter.values()), bins=50, alpha=0.7, edgecolor='black')
    plt.title('Distribution of Images per Device')
    plt.xlabel('Number of Images per Device')
    plt.ylabel('Number of Devices')
    plt.yscale('log')
    
    # Plot 4: Pie chart of top 10 devices
    plt.subplot(2, 2, 4)
    top_10_devices = device_counter.most_common(10)
    device_names = [f"Device {d[0]}" for d in top_10_devices]
    device_counts = [d[1] for d in top_10_devices]
    
    plt.pie(device_counts, labels=device_names, autopct='%1.1f%%', startangle=90)
    plt.title('Top 10 Devices (Percentage of Total Images)')
    
    plt.tight_layout()
    
    # Save visualization
    viz_file = "/data/exports/device_id_analysis.png"
    plt.savefig(viz_file, dpi=300, bbox_inches='tight')
    print(f"Visualization saved to {viz_file}")
    
    # Create CSV for federated learning
    df = pd.DataFrame(filename_patterns)
    csv_file = "/data/exports/device_image_mapping.csv"
    df.to_csv(csv_file, index=False)
    print(f"Device-image mapping saved to {csv_file}")
    
    return device_counter, filename_patterns

def prepare_federated_learning_data():
    """Prepare data for federated learning"""
    device_counter, filename_patterns = extract_device_ids()
    
    # Filter devices with sufficient data (at least 10 images)
    sufficient_devices = {device_id: count for device_id, count in device_counter.items() if count >= 10}
    
    print(f"\nDevices with sufficient data (≥10 images): {len(sufficient_devices)}")
    
    # Create federated learning configuration
    fl_config = {
        'total_devices': len(sufficient_devices),
        'min_images_per_device': 10,
        'total_images': sum(sufficient_devices.values()),
        'device_list': list(sufficient_devices.keys()),
        'device_counts': dict(sufficient_devices)
    }
    
    # Save FL configuration
    fl_config_file = "/data/exports/federated_learning_config.json"
    with open(fl_config_file, 'w') as f:
        json.dump(fl_config, f, indent=2)
    
    print(f"Federated learning configuration saved to {fl_config_file}")
    
    return fl_config

if __name__ == "__main__":
    fl_config = prepare_federated_learning_data()
    
    print("\nFederated Learning Setup Complete!")
    print(f"Ready to train with {fl_config['total_devices']} devices")
    print(f"Total images for federated learning: {fl_config['total_images']}") 