"""
Example: Using DINO for CREDO Image Processing

Based on Zichun's recommendations, this example shows how to:
1. Load CREDO images
2. Use pre-trained DINO-v2 models
3. Extract features or fine-tune for cosmic ray detection
"""

import torch
from torch.utils.data import DataLoader
from credo import CREDOImageDataset, DINOImageEncoder, load_credo_images


def example_1_load_images():
    """Load CREDO images from JSON file."""
    print("Example 1: Loading CREDO images from JSON")
    
    # Load images from JSON export
    dataset = load_credo_images(
        source='scripts/data/credo_images_export.json',
        image_key='frame_content',
        image_size=224,  # DINO standard size
    )
    
    print(f"Loaded {len(dataset)} images")
    
    # Create DataLoader
    dataloader = DataLoader(dataset, batch_size=8, shuffle=True)
    
    # Get a batch
    batch = next(iter(dataloader))
    images = batch['image']  # [batch, 3, 224, 224]
    metadata = batch['metadata']
    
    print(f"Batch shape: {images.shape}")
    print(f"Metadata keys: {list(metadata[0].keys())}")
    
    return dataset, dataloader


def example_2_extract_features():
    """Extract features using pre-trained DINO-v2."""
    print("\nExample 2: Extracting features with DINO-v2")
    
    # Load encoder
    encoder = DINOImageEncoder.from_pretrained(
        model_name='facebook/dinov2-base',
        freeze_backbone=True,  # Use pre-trained weights only
    )
    encoder.eval()
    
    # Load images
    dataset = load_credo_images(
        source='scripts/data/credo_images_export.json',
        image_size=224,
    )
    dataloader = DataLoader(dataset, batch_size=8)
    
    # Extract features
    all_features = []
    with torch.no_grad():
        for batch in dataloader:
            images = batch['image']
            features = encoder.extract_features(images)  # [batch, 768]
            all_features.append(features)
    
    features = torch.cat(all_features, dim=0)
    print(f"Extracted features shape: {features.shape}")
    print(f"Feature dimension: {features.shape[1]}")
    
    return features


def example_3_fine_tune():
    """Fine-tune DINO for cosmic ray detection."""
    print("\nExample 3: Fine-tuning DINO for classification")
    
    # Create model with classification head
    encoder = DINOImageEncoder.from_pretrained(
        model_name='facebook/dinov2-base',
        freeze_backbone=False,  # Allow fine-tuning
    )
    
    # Add classification head
    model = encoder.fine_tune_for_classification(
        num_classes=2,  # Binary: cosmic ray / not
        freeze_backbone=False,
    )
    
    print("Model structure:")
    print(model)
    
    # Example training loop
    dataset = load_credo_images(
        source='scripts/data/credo_images_export.json',
        image_size=224,
    )
    dataloader = DataLoader(dataset, batch_size=8, shuffle=True)
    
    # Dummy labels (replace with actual labels)
    criterion = torch.nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
    
    model.train()
    for epoch in range(1):  # Just one epoch for example
        for batch in dataloader:
            images = batch['image']
            # labels = batch['labels']  # Add labels to dataset
            
            # Forward pass
            image_features = encoder(images, return_pooled=True)
            # logits = model['classifier'](image_features)
            # loss = criterion(logits, labels)
            
            # Backward pass
            # loss.backward()
            # optimizer.step()
            # optimizer.zero_grad()
    
    print("Fine-tuning setup complete!")
    
    return model


def example_4_elasticsearch():
    """Load images from Elasticsearch."""
    print("\nExample 4: Loading from Elasticsearch")
    
    from elasticsearch import Elasticsearch
    
    # Connect to Elasticsearch
    es = Elasticsearch(
        ['https://localhost:9200'],
        basic_auth=('elastic', 'your-password'),
        verify_certs=False,
    )
    
    # Load images
    dataset = load_credo_images(
        source='credo-detections',
        es_client=es,
        query={'term': {'source': 'credo-science'}},
        size=100,
        image_key='frame_content',
    )
    
    print(f"Loaded {len(dataset)} images from Elasticsearch")
    
    return dataset


if __name__ == '__main__':
    print("=" * 60)
    print("CREDO DINO Examples")
    print("Based on Zichun's Recommendations")
    print("=" * 60)
    
    # Run examples
    # example_1_load_images()
    # example_2_extract_features()
    # example_3_fine_tune()
    # example_4_elasticsearch()
    
    print("\nNote: Uncomment examples to run them")
    print("Make sure you have CREDO image data available!")


