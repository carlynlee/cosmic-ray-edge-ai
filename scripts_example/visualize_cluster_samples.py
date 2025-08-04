#!/usr/bin/env python3
"""
Visualize sample images from each cluster
Shows what types of images are grouped together in each cluster
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from PIL import Image
import numpy as np
import random
from pathlib import Path

def load_cluster_data():
    """Load cluster assignments"""
    cluster_file = "/data/exports/cluster_results.txt"
    if not os.path.exists(cluster_file):
        print("Cluster results not found!")
        return None
    
    df = pd.read_csv(cluster_file)
    return df

def get_cluster_distribution(df):
    """Get distribution of images across clusters"""
    cluster_counts = df['Cluster'].value_counts().to_dict()
    
    print("Cluster Distribution:")
    for cluster_id, count in sorted(cluster_counts.items()):
        print(f"  Cluster {cluster_id}: {count} images")
    
    return cluster_counts

def visualize_cluster_samples(df, samples_per_cluster=5):
    """Visualize sample images from each cluster"""
    
    # Get unique clusters
    clusters = sorted(df['Cluster'].unique())
    
    # Create subplot grid
    num_clusters = len(clusters)
    fig, axes = plt.subplots(samples_per_cluster, num_clusters, 
                             figsize=(num_clusters * 3, samples_per_cluster * 3))
    
    if num_clusters == 1:
        axes = axes.reshape(-1, 1)
    
    print(f"Visualizing {samples_per_cluster} samples from each of {num_clusters} clusters...")
    
    for cluster_idx, cluster_id in enumerate(clusters):
        # Get images for this cluster
        cluster_images = df[df['Cluster'] == cluster_id]['Image_Path'].tolist()
        
        print(f"Cluster {cluster_id}: {len(cluster_images)} images available")
        
        # Sample random images from this cluster
        if len(cluster_images) >= samples_per_cluster:
            sample_images = random.sample(cluster_images, samples_per_cluster)
        else:
            sample_images = cluster_images
            print(f"  Warning: Only {len(cluster_images)} images available for cluster {cluster_id}")
        
        # Display sample images
        for img_idx, img_path in enumerate(sample_images):
            try:
                # Load and display image
                img = mpimg.imread(img_path)
                
                if num_clusters == 1:
                    ax = axes[img_idx]
                else:
                    ax = axes[img_idx, cluster_idx]
                
                ax.imshow(img)
                ax.set_title(f'Cluster {cluster_id}\n{os.path.basename(img_path)}', 
                           fontsize=10, wrap=True)
                ax.axis('off')
                
            except Exception as e:
                print(f"Error loading {img_path}: {e}")
                # Create empty plot with error message
                if num_clusters == 1:
                    ax = axes[img_idx]
                else:
                    ax = axes[img_idx, cluster_idx]
                
                ax.text(0.5, 0.5, f'Error loading\n{os.path.basename(img_path)}', 
                       ha='center', va='center', transform=ax.transAxes)
                ax.axis('off')
    
    plt.tight_layout()
    
    # Save visualization
    viz_file = "/data/exports/cluster_samples_visualization.png"
    plt.savefig(viz_file, dpi=300, bbox_inches='tight')
    print(f"Cluster samples visualization saved to {viz_file}")
    
    return fig

def create_cluster_summary(df):
    """Create a summary of each cluster with statistics"""
    
    clusters = sorted(df['Cluster'].unique())
    
    print("\n" + "="*60)
    print("CLUSTER SUMMARY")
    print("="*60)
    
    for cluster_id in clusters:
        cluster_data = df[df['Cluster'] == cluster_id]
        cluster_images = cluster_data['Image_Path'].tolist()
        
        print(f"\n📊 Cluster {cluster_id}:")
        print(f"   • Total images: {len(cluster_images)}")
        print(f"   • Sample filenames:")
        
        # Show first 5 filenames
        for i, img_path in enumerate(cluster_images[:5]):
            filename = os.path.basename(img_path)
            print(f"     {i+1}. {filename}")
        
        if len(cluster_images) > 5:
            print(f"     ... and {len(cluster_images) - 5} more images")
    
    print("\n" + "="*60)

def create_cluster_grid(df, max_images_per_cluster=20):
    """Create a grid visualization showing more images per cluster"""
    
    clusters = sorted(df['Cluster'].unique())
    
    # Calculate grid dimensions
    num_clusters = len(clusters)
    max_images = max_images_per_cluster
    
    # Create figure
    fig, axes = plt.subplots(max_images, num_clusters, 
                             figsize=(num_clusters * 2, max_images * 1.5))
    
    if num_clusters == 1:
        axes = axes.reshape(-1, 1)
    
    print(f"Creating detailed grid visualization...")
    
    for cluster_idx, cluster_id in enumerate(clusters):
        # Get images for this cluster
        cluster_images = df[df['Cluster'] == cluster_id]['Image_Path'].tolist()
        
        # Sample images (or use all if less than max)
        if len(cluster_images) >= max_images:
            sample_images = random.sample(cluster_images, max_images)
        else:
            sample_images = cluster_images
        
        # Display images in grid
        for img_idx, img_path in enumerate(sample_images):
            try:
                # Load and display image
                img = mpimg.imread(img_path)
                
                if num_clusters == 1:
                    ax = axes[img_idx]
                else:
                    ax = axes[img_idx, cluster_idx]
                
                ax.imshow(img)
                ax.set_title(f'{os.path.basename(img_path)}', fontsize=8)
                ax.axis('off')
                
            except Exception as e:
                print(f"Error loading {img_path}: {e}")
                if num_clusters == 1:
                    ax = axes[img_idx]
                else:
                    ax = axes[img_idx, cluster_idx]
                
                ax.text(0.5, 0.5, 'Error', ha='center', va='center', transform=ax.transAxes)
                ax.axis('off')
        
        # Fill remaining slots with empty plots
        for img_idx in range(len(sample_images), max_images):
            if num_clusters == 1:
                ax = axes[img_idx]
            else:
                ax = axes[img_idx, cluster_idx]
            
            ax.axis('off')
    
    plt.tight_layout()
    
    # Save detailed visualization
    viz_file = "/data/exports/cluster_detailed_grid.png"
    plt.savefig(viz_file, dpi=300, bbox_inches='tight')
    print(f"Detailed cluster grid saved to {viz_file}")
    
    return fig

def main():
    """Main function to visualize cluster samples"""
    print("Visualizing cluster samples...")
    
    # Load cluster data
    df = load_cluster_data()
    if df is None:
        return
    
    # Get cluster distribution
    cluster_counts = get_cluster_distribution(df)
    
    # Create cluster summary
    create_cluster_summary(df)
    
    # Create sample visualization (5 images per cluster)
    print("\nCreating sample visualization...")
    fig1 = visualize_cluster_samples(df, samples_per_cluster=5)
    
    # Create detailed grid visualization
    print("\nCreating detailed grid visualization...")
    fig2 = create_cluster_grid(df, max_images_per_cluster=10)
    
    print("\nVisualization complete!")
    print("Files created:")
    print("  - /data/exports/cluster_samples_visualization.png")
    print("  - /data/exports/cluster_detailed_grid.png")

if __name__ == "__main__":
    main() 