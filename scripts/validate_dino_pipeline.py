"""
Validate the DINO pipeline end-to-end using sample CREDO images.

Tests:
  1. CREDOImageDataset loading from file paths
  2. Image preprocessing (decode, resize, normalize)
  3. DINOv2 feature extraction
  4. Feature space analysis (stats, pairwise similarity)
  5. Classification head setup
"""

import sys
import os
import time
import glob

import torch
import numpy as np
from torch.utils.data import DataLoader

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from credo import CREDOImageDataset, DINOImageEncoder


SAMPLE_DIR = os.path.join(os.path.dirname(__file__), 'data', 'sample_images')
DINO_MODEL = 'facebook/dinov2-base'


def find_sample_images():
    paths = sorted(glob.glob(os.path.join(SAMPLE_DIR, '*.png')))
    if not paths:
        print(f"FAIL: No PNG images found in {SAMPLE_DIR}")
        sys.exit(1)
    print(f"Found {len(paths)} sample images in {SAMPLE_DIR}")
    for p in paths:
        print(f"  - {os.path.basename(p)}")
    return paths


def test_dataset_loading(image_paths):
    """Test 1: Load images through CREDOImageDataset."""
    print("\n" + "=" * 60)
    print("TEST 1: Dataset Loading")
    print("=" * 60)

    images = [{'frame_content': p} for p in image_paths]
    dataset = CREDOImageDataset(images, image_size=224, image_key='frame_content')

    print(f"  Dataset size: {len(dataset)}")
    assert len(dataset) == len(image_paths), "Dataset size mismatch"

    sample = dataset[0]
    img_tensor = sample['image']
    print(f"  Image tensor shape: {img_tensor.shape}")
    print(f"  Image tensor dtype: {img_tensor.dtype}")
    print(f"  Pixel range: [{img_tensor.min():.4f}, {img_tensor.max():.4f}]")
    assert img_tensor.shape == (3, 224, 224), f"Unexpected shape: {img_tensor.shape}"
    assert img_tensor.dtype == torch.float32, f"Unexpected dtype: {img_tensor.dtype}"

    dataloader = DataLoader(dataset, batch_size=len(image_paths), shuffle=False)
    batch = next(iter(dataloader))
    batch_imgs = batch['image']
    print(f"  Batch shape: {batch_imgs.shape}")
    assert batch_imgs.shape == (len(image_paths), 3, 224, 224)

    print("  PASS")
    return dataset, dataloader


def test_dino_loading():
    """Test 2: Load DINOv2 model."""
    print("\n" + "=" * 60)
    print("TEST 2: DINOv2 Model Loading")
    print("=" * 60)

    t0 = time.time()
    encoder = DINOImageEncoder.from_pretrained(
        model_name=DINO_MODEL,
        freeze_backbone=True,
    )
    load_time = time.time() - t0

    print(f"  Model: {DINO_MODEL}")
    print(f"  Load time: {load_time:.1f}s")
    print(f"  Hidden dim: {encoder.hidden_dim}")
    print(f"  Backbone parameters: {sum(p.numel() for p in encoder.model.parameters()):,}")
    print(f"  Trainable parameters: {sum(p.numel() for p in encoder.model.parameters() if p.requires_grad):,}")

    assert encoder.hidden_dim == 768, f"Unexpected hidden dim: {encoder.hidden_dim}"
    print("  PASS")
    return encoder


def test_feature_extraction(encoder, dataloader):
    """Test 3: Extract features from sample images."""
    print("\n" + "=" * 60)
    print("TEST 3: Feature Extraction")
    print("=" * 60)

    encoder.eval()
    batch = next(iter(dataloader))
    images = batch['image']

    t0 = time.time()
    with torch.no_grad():
        pooled = encoder(images, return_pooled=True)
    inference_time = time.time() - t0

    print(f"  Input shape:  {images.shape}")
    print(f"  Output shape: {pooled.shape}")
    print(f"  Inference time: {inference_time:.3f}s ({inference_time/len(images)*1000:.1f}ms/image)")

    assert pooled.shape == (len(images), 768), f"Unexpected output shape: {pooled.shape}"
    assert not torch.isnan(pooled).any(), "NaN in features"
    assert not torch.isinf(pooled).any(), "Inf in features"

    print(f"  Feature mean: {pooled.mean():.4f}")
    print(f"  Feature std:  {pooled.std():.4f}")
    print(f"  Feature norm (mean): {torch.norm(pooled, dim=1).mean():.4f}")

    print("  PASS")
    return pooled


def test_normalized_features(encoder, dataloader):
    """Test 4: extract_features() with L2 normalization."""
    print("\n" + "=" * 60)
    print("TEST 4: Normalized Feature Extraction")
    print("=" * 60)

    encoder.eval()
    batch = next(iter(dataloader))
    images = batch['image']

    features = encoder.extract_features(images, normalize=True)
    norms = torch.norm(features, dim=1)

    print(f"  Feature shape: {features.shape}")
    print(f"  L2 norms: {norms.tolist()}")
    assert torch.allclose(norms, torch.ones_like(norms), atol=1e-5), "Features not unit-normalized"

    print("  PASS")
    return features


def test_pairwise_similarity(features, image_paths):
    """Test 5: Pairwise cosine similarity between sample images."""
    print("\n" + "=" * 60)
    print("TEST 5: Pairwise Cosine Similarity")
    print("=" * 60)

    sim_matrix = features @ features.T
    names = [os.path.basename(p).replace('.png', '') for p in image_paths]

    print(f"\n  {'':>14s}", end='')
    for n in names:
        print(f"  {n:>12s}", end='')
    print()

    for i, ni in enumerate(names):
        print(f"  {ni:>14s}", end='')
        for j in range(len(names)):
            val = sim_matrix[i, j].item()
            print(f"  {val:>12.4f}", end='')
        print()

    off_diag = sim_matrix[~torch.eye(len(names), dtype=bool)]
    print(f"\n  Off-diagonal similarity: mean={off_diag.mean():.4f}, "
          f"min={off_diag.min():.4f}, max={off_diag.max():.4f}")

    print("  PASS")


def test_classification_head(encoder):
    """Test 6: Classification head for fine-tuning."""
    print("\n" + "=" * 60)
    print("TEST 6: Classification Head")
    print("=" * 60)

    model = encoder.fine_tune_for_classification(num_classes=2, freeze_backbone=True)

    print(f"  Components: {list(model.keys())}")
    print(f"  Classifier architecture:")
    for name, layer in model['classifier'].named_children():
        print(f"    [{name}] {layer}")

    dummy_input = torch.randn(2, 3, 224, 224)
    with torch.no_grad():
        backbone_out = model['backbone'](pixel_values=dummy_input)
        cls_features = backbone_out.last_hidden_state[:, 0, :]
        logits = model['classifier'](cls_features)

    print(f"  Backbone output: {cls_features.shape}")
    print(f"  Logits shape: {logits.shape}")
    print(f"  Logits: {logits}")
    assert logits.shape == (2, 2), f"Unexpected logits shape: {logits.shape}"

    print("  PASS")


def test_full_sequence(encoder, dataloader, image_paths):
    """Test 7: Full sequence — images through backbone then classifier."""
    print("\n" + "=" * 60)
    print("TEST 7: End-to-End Forward Pass (backbone + classifier)")
    print("=" * 60)

    model = encoder.fine_tune_for_classification(num_classes=2, freeze_backbone=True)
    batch = next(iter(dataloader))
    images = batch['image']

    with torch.no_grad():
        backbone_out = model['backbone'](pixel_values=images)
        cls_features = backbone_out.last_hidden_state[:, 0, :]
        logits = model['classifier'](cls_features)
        probs = torch.softmax(logits, dim=1)

    names = [os.path.basename(p).replace('.png', '') for p in image_paths]
    print(f"\n  {'Image':>14s}  {'Class 0':>8s}  {'Class 1':>8s}  Predicted")
    print(f"  {'-'*14}  {'-'*8}  {'-'*8}  {'-'*9}")
    for i, name in enumerate(names):
        p0, p1 = probs[i][0].item(), probs[i][1].item()
        pred = 1 if p1 > p0 else 0
        print(f"  {name:>14s}  {p0:>8.4f}  {p1:>8.4f}  class {pred}")

    print("\n  (Predictions are random — model is untrained. This validates the forward pass.)")
    print("  PASS")


def main():
    print("=" * 60)
    print("DINO Pipeline Validation")
    print(f"Model: {DINO_MODEL}")
    print("=" * 60)

    image_paths = find_sample_images()
    dataset, dataloader = test_dataset_loading(image_paths)
    encoder = test_dino_loading()
    pooled = test_feature_extraction(encoder, dataloader)
    features = test_normalized_features(encoder, dataloader)
    test_pairwise_similarity(features, image_paths)
    test_classification_head(encoder)
    test_full_sequence(encoder, dataloader, image_paths)

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)
    print(f"\nSummary:")
    print(f"  - Loaded {len(image_paths)} CREDO images from disk")
    print(f"  - Preprocessed to 224x224 with ImageNet normalization")
    print(f"  - Extracted 768-dim features via DINOv2-base")
    print(f"  - L2-normalized features are unit vectors")
    print(f"  - Classification head produces 2-class logits")
    print(f"  - End-to-end forward pass works")
    print(f"\nDINO pipeline is validated and ready for use.")


if __name__ == '__main__':
    main()
