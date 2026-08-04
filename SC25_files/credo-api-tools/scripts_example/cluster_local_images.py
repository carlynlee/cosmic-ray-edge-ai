#!/usr/bin/env python3
"""
Script to cluster images from the extracted hit-images-final.zip
This version works with local images without requiring Elasticsearch
"""
import os
import numpy as np
from tensorflow.keras.applications.resnet50 import ResNet50, preprocess_input
from tensorflow.keras.preprocessing.image import img_to_array, load_img
from tensorflow.keras.models import Model
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import joblib
from PIL import Image
import glob
from pathlib import Path

# Settings
img_dir = "/data/images"
model_path = '/data/models/kmeans_model.pkl'
n_clusters = 10

# Load pre-trained ResNet50 model for feature extraction
print("Loading ResNet50 model...")
base_model = ResNet50(weights='imagenet', include_top=False, pooling='avg')
feature_extraction_model = Model(inputs=base_model.input, outputs=base_model.output)

def extract_features(image_path, model):
    """Extract features from an image file"""
    try:
        # Load and preprocess image
        img = load_img(image_path, target_size=(224, 224))
        img_array = img_to_array(img)
        img_array_expanded = np.expand_dims(img_array, axis=0)
        img_preprocessed = preprocess_input(img_array_expanded)
        
        # Extract features
        features = model.predict(img_preprocessed, verbose=0)
        return features.flatten()
    except Exception as e:
        print(f"Failed to extract features from {image_path}: {str(e)}")
        return None

def main():
    print("Starting image clustering...")
    
    # Find all image files
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff']
    image_files = []
    
    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(img_dir, '**', ext), recursive=True))
        image_files.extend(glob.glob(os.path.join(img_dir, '**', ext.upper()), recursive=True))
    
    print(f"Found {len(image_files)} image files")
    
    if len(image_files) == 0:
        print("No image files found!")
        return
    
    # Extract features from images
    print("Extracting features from images...")
    features_list = []
    valid_image_paths = []
    
    for i, image_path in enumerate(image_files):
        if i % 100 == 0:
            print(f"Processing image {i+1}/{len(image_files)}")
        
        features = extract_features(image_path, feature_extraction_model)
        if features is not None:
            features_list.append(features)
            valid_image_paths.append(image_path)
    
    print(f"Successfully extracted features from {len(features_list)} images")
    
    if len(features_list) == 0:
        print("No valid features extracted!")
        return
    
    # Convert to numpy array
    features_array = np.array(features_list)
    
    # Check if model exists
    if os.path.exists(model_path):
        print("Loading existing KMeans model...")
        kmeans = joblib.load(model_path)
        clusters = kmeans.predict(features_array)
    else:
        print("Training new KMeans model...")
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = kmeans.fit_predict(features_array)
        
        # Save the model
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        joblib.dump(kmeans, model_path)
        print(f"Model saved to {model_path}")
    
    # Print cluster statistics
    unique, counts = np.unique(clusters, return_counts=True)
    print("\nCluster Statistics:")
    for cluster_id, count in zip(unique, counts):
        print(f"Cluster {cluster_id}: {count} images")
    
    # Save cluster assignments
    cluster_results = []
    for image_path, cluster_id in zip(valid_image_paths, clusters):
        cluster_results.append({
            'image_path': image_path,
            'cluster': int(cluster_id)
        })
    
    # Save results
    results_file = '/data/exports/cluster_results.txt'
    os.makedirs(os.path.dirname(results_file), exist_ok=True)
    
    with open(results_file, 'w') as f:
        f.write("Image_Path,Cluster\n")
        for result in cluster_results:
            f.write(f"{result['image_path']},{result['cluster']}\n")
    
    print(f"\nResults saved to {results_file}")
    
    # Visualize clusters with PCA
    print("Creating PCA visualization...")
    pca = PCA(n_components=2)
    reduced_features = pca.fit_transform(features_array)
    
    plt.figure(figsize=(12, 8))
    scatter = plt.scatter(reduced_features[:, 0], reduced_features[:, 1], 
                         c=clusters, cmap='viridis', alpha=0.6)
    plt.colorbar(scatter)
    plt.title(f'2D PCA of Image Clusters (n={len(features_list)})')
    plt.xlabel('Principal Component 1')
    plt.ylabel('Principal Component 2')
    plt.grid(True, alpha=0.3)
    
    # Save plot
    plot_file = '/data/exports/cluster_visualization.png'
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"Visualization saved to {plot_file}")
    
    print("\nClustering complete!")
    print(f"Total images processed: {len(features_list)}")
    print(f"Number of clusters: {n_clusters}")

if __name__ == "__main__":
    main() 