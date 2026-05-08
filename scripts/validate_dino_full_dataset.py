"""
Validate DINO feature extraction on the full labeled CREDO dataset.

Runs DINOv2 on all 2,354 human-labeled images across 4 categories:
  - artefacts (1122)
  - hits_votes_4_Dots (535)
  - hits_votes_4_Lines (393)
  - hits_votes_4_Worms (304)

Produces:
  1. Per-category feature statistics
  2. Within-class vs between-class cosine similarity
  3. Category centroid similarity matrix
  4. t-SNE or PCA visualization saved as PNG
"""

import sys
import os
import time
import glob

import torch
import numpy as np
from torch.utils.data import DataLoader
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from credo import CREDOImageDataset, DINOImageEncoder


DATA_DIR = os.path.join(os.path.dirname(__file__), 'data', 'hit-images-final')
DINO_MODEL = 'facebook/dinov2-base'
BATCH_SIZE = 32
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'models', 'dino_analysis')

CATEGORIES = ['artefacts', 'hits_votes_4_Dots', 'hits_votes_4_Lines', 'hits_votes_4_Worms']
SHORT_NAMES = {'artefacts': 'Artefacts', 'hits_votes_4_Dots': 'Dots',
               'hits_votes_4_Lines': 'Lines', 'hits_votes_4_Worms': 'Worms'}


def load_labeled_images():
    """Load all images with their category labels."""
    all_images = []
    labels = []

    for cat in CATEGORIES:
        cat_dir = os.path.join(DATA_DIR, cat)
        paths = sorted(glob.glob(os.path.join(cat_dir, '*.png')))
        print(f"  {SHORT_NAMES[cat]:>10s}: {len(paths)} images")
        for p in paths:
            all_images.append({'frame_content': p, 'category': cat})
            labels.append(cat)

    print(f"  {'Total':>10s}: {len(all_images)} images")
    return all_images, labels


def extract_all_features(encoder, all_images):
    """Extract DINO features for all images."""
    dataset = CREDOImageDataset(all_images, image_size=224, image_key='frame_content')
    dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    all_features = []
    encoder.eval()

    t0 = time.time()
    with torch.no_grad():
        for i, batch in enumerate(dataloader):
            images = batch['image']
            features = encoder.extract_features(images, normalize=True)
            all_features.append(features.cpu())
            if (i + 1) % 10 == 0 or (i + 1) == len(dataloader):
                done = min((i + 1) * BATCH_SIZE, len(dataset))
                elapsed = time.time() - t0
                print(f"    Processed {done}/{len(dataset)} images ({elapsed:.1f}s)")

    features = torch.cat(all_features, dim=0)
    total_time = time.time() - t0
    print(f"  Feature extraction complete: {features.shape} in {total_time:.1f}s "
          f"({total_time/len(dataset)*1000:.1f}ms/image)")
    return features


def analyze_features(features, labels):
    """Compute within-class and between-class similarity statistics."""
    unique_cats = CATEGORIES
    cat_indices = {cat: [] for cat in unique_cats}
    for i, label in enumerate(labels):
        cat_indices[label].append(i)

    print("\n  Per-category feature statistics:")
    print(f"  {'Category':>10s}  {'Count':>5s}  {'Mean Norm':>10s}  {'Mean Sim':>10s}  {'Std Sim':>8s}")
    print(f"  {'-'*10}  {'-'*5}  {'-'*10}  {'-'*10}  {'-'*8}")

    centroids = {}
    within_sims = {}

    for cat in unique_cats:
        idx = cat_indices[cat]
        cat_feats = features[idx]
        centroids[cat] = cat_feats.mean(dim=0)
        centroids[cat] = centroids[cat] / centroids[cat].norm()

        sim = cat_feats @ cat_feats.T
        mask = ~torch.eye(len(idx), dtype=bool)
        within = sim[mask]
        within_sims[cat] = within

        norms = torch.norm(cat_feats, dim=1)
        print(f"  {SHORT_NAMES[cat]:>10s}  {len(idx):>5d}  {norms.mean():>10.4f}  "
              f"{within.mean():>10.4f}  {within.std():>8.4f}")

    # Between-class similarity
    print("\n  Between-class centroid cosine similarity:")
    names = [SHORT_NAMES[c] for c in unique_cats]
    print(f"  {'':>10s}", end='')
    for n in names:
        print(f"  {n:>10s}", end='')
    print()

    centroid_matrix = torch.zeros(len(unique_cats), len(unique_cats))
    for i, ci in enumerate(unique_cats):
        print(f"  {names[i]:>10s}", end='')
        for j, cj in enumerate(unique_cats):
            sim = (centroids[ci] @ centroids[cj]).item()
            centroid_matrix[i, j] = sim
            print(f"  {sim:>10.4f}", end='')
        print()

    # Summary
    all_within = torch.cat(list(within_sims.values()))
    between_sims = []
    for i, ci in enumerate(unique_cats):
        for j, cj in enumerate(unique_cats):
            if i < j:
                cross = features[cat_indices[ci]] @ features[cat_indices[cj]].T
                between_sims.append(cross.flatten())
    all_between = torch.cat(between_sims)

    print(f"\n  Within-class similarity:  mean={all_within.mean():.4f}, std={all_within.std():.4f}")
    print(f"  Between-class similarity: mean={all_between.mean():.4f}, std={all_between.std():.4f}")
    gap = all_within.mean() - all_between.mean()
    print(f"  Separation gap:           {gap:.4f}")

    return centroids, cat_indices, centroid_matrix


def compute_clustering_quality(features, labels):
    """Compute silhouette score to measure cluster quality."""
    label_ids = [CATEGORIES.index(l) for l in labels]
    score = silhouette_score(features.numpy(), label_ids, metric='cosine', sample_size=min(2000, len(labels)))
    print(f"\n  Silhouette score (cosine): {score:.4f}")
    print(f"    (1.0 = perfect separation, 0.0 = overlapping, <0 = wrong clusters)")
    return score


def plot_pca(features, labels, cat_indices, output_path):
    """PCA projection of features, colored by category."""
    pca = PCA(n_components=2)
    proj = pca.fit_transform(features.numpy())

    colors = {'artefacts': '#ff6b35', 'hits_votes_4_Dots': '#00d4aa',
              'hits_votes_4_Lines': '#7b68ee', 'hits_votes_4_Worms': '#ffcc00'}

    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    fig.patch.set_facecolor('#0a0a0f')
    ax.set_facecolor('#0a0a0f')

    for cat in CATEGORIES:
        idx = cat_indices[cat]
        ax.scatter(proj[idx, 0], proj[idx, 1], c=colors[cat], label=SHORT_NAMES[cat],
                   alpha=0.5, s=12, edgecolors='none')

    ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% variance)',
                  color='#e8e8f0', fontsize=11)
    ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}% variance)',
                  color='#e8e8f0', fontsize=11)
    ax.set_title('DINO Feature Space — CREDO Image Categories (PCA)', color='#e8e8f0',
                 fontsize=14, fontweight='bold', pad=15)
    ax.legend(loc='upper right', fontsize=10, framealpha=0.3, facecolor='#14141f',
              edgecolor='#2a2a3a', labelcolor='#e8e8f0')
    ax.tick_params(colors='#6a6a8a')
    for spine in ax.spines.values():
        spine.set_color('#2a2a3a')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor='#0a0a0f', bbox_inches='tight')
    plt.close()
    print(f"\n  PCA plot saved to: {output_path}")
    print(f"  Variance explained: PC1={pca.explained_variance_ratio_[0]*100:.1f}%, "
          f"PC2={pca.explained_variance_ratio_[1]*100:.1f}%")


def plot_centroid_heatmap(centroid_matrix, output_path):
    """Plot centroid similarity as a heatmap."""
    names = [SHORT_NAMES[c] for c in CATEGORIES]

    fig, ax = plt.subplots(1, 1, figsize=(6, 5))
    fig.patch.set_facecolor('#0a0a0f')
    ax.set_facecolor('#0a0a0f')

    im = ax.imshow(centroid_matrix.numpy(), cmap='RdYlGn', vmin=0.5, vmax=1.0, aspect='equal')
    ax.set_xticks(range(len(names)))
    ax.set_yticks(range(len(names)))
    ax.set_xticklabels(names, color='#e8e8f0', fontsize=10, rotation=45, ha='right')
    ax.set_yticklabels(names, color='#e8e8f0', fontsize=10)

    for i in range(len(names)):
        for j in range(len(names)):
            val = centroid_matrix[i, j].item()
            color = '#0a0a0f' if val > 0.85 else '#e8e8f0'
            ax.text(j, i, f'{val:.3f}', ha='center', va='center', fontsize=11,
                    fontweight='bold', color=color)

    ax.set_title('Category Centroid Cosine Similarity', color='#e8e8f0',
                 fontsize=13, fontweight='bold', pad=12)
    cbar = plt.colorbar(im, ax=ax, shrink=0.8)
    cbar.ax.tick_params(colors='#6a6a8a')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor='#0a0a0f', bbox_inches='tight')
    plt.close()
    print(f"  Centroid heatmap saved to: {output_path}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("DINO Full Dataset Validation")
    print(f"Model: {DINO_MODEL}")
    print(f"Data:  {DATA_DIR}")
    print("=" * 60)

    print("\nLoading labeled images...")
    all_images, labels = load_labeled_images()

    print("\nLoading DINOv2 model...")
    encoder = DINOImageEncoder.from_pretrained(DINO_MODEL, freeze_backbone=True)
    print(f"  Model loaded: {encoder.hidden_dim}-dim features, "
          f"{sum(p.numel() for p in encoder.model.parameters()):,} parameters")

    print("\nExtracting features...")
    features = extract_all_features(encoder, all_images)

    print("\n" + "=" * 60)
    print("FEATURE SPACE ANALYSIS")
    print("=" * 60)
    centroids, cat_indices, centroid_matrix = analyze_features(features, labels)
    silhouette = compute_clustering_quality(features, labels)

    print("\n" + "=" * 60)
    print("GENERATING VISUALIZATIONS")
    print("=" * 60)
    pca_path = os.path.join(OUTPUT_DIR, 'dino_pca_categories.png')
    heatmap_path = os.path.join(OUTPUT_DIR, 'dino_centroid_similarity.png')
    plot_pca(features, labels, cat_indices, pca_path)
    plot_centroid_heatmap(centroid_matrix, heatmap_path)

    # Save features for later use
    torch.save({
        'features': features,
        'labels': labels,
        'categories': CATEGORIES,
        'model': DINO_MODEL,
    }, os.path.join(OUTPUT_DIR, 'dino_features.pt'))
    print(f"\n  Features saved to: {os.path.join(OUTPUT_DIR, 'dino_features.pt')}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Images processed:    {len(labels)}")
    print(f"  Categories:          {len(CATEGORIES)}")
    print(f"  Feature dimension:   {features.shape[1]}")
    print(f"  Silhouette score:    {silhouette:.4f}")
    print(f"  Outputs in:          {OUTPUT_DIR}/")
    print("=" * 60)


if __name__ == '__main__':
    main()
