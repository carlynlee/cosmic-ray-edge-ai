import matplotlib.pyplot as plt
import numpy as np
import base64
from PIL import Image
from io import BytesIO
from elasticsearch import Elasticsearch

# Initialize Elasticsearch client
es = Elasticsearch()


def decode_image_base64(image_base64, size=(256, 256)):
    """Decode an image from a base64 encoding and resize it to the specified size."""
    image_data = base64.b64decode(image_base64)
    image = Image.open(BytesIO(image_data))
    image = image.convert('RGB')  # Convert image to RGB
    image = image.resize(size, Image.ANTIALIAS)  # Resize image to ensure uniformity
    return image


def fetch_images(device_id, cluster_id):
    """Fetch images from Elasticsearch based on device_id and cluster_id."""
    query = {
        "size": 1000,
        "query": {
            "bool": {
                "must": [
                    {"term": {"device_id": device_id}},
                    {"term": {"cluster": cluster_id}},
                    {"range": {"timestamp": {"gte": "2018-10-01T00:00:00", "lte": "2018-10-31T23:59:59"}}}
                ]
            }
        }
    }
    response = es.search(index="credo-detections", body=query)
    images = []
    for hit in response['hits']['hits']:
        image_base64 = hit['_source']['frame_content']
        image = decode_image_base64(image_base64)
        images.append(np.array(image))
    return images


def plot_mean_images_grid(device_ids, cluster_ids):
    num_devices = len(device_ids)
    num_clusters = len(cluster_ids)
    fig, axes = plt.subplots(nrows=num_devices, ncols=num_clusters, figsize=(num_clusters * 3, num_devices * 3))
    fig.suptitle('Mean Images for Clusters by Device', fontsize=16)

    for i, device_id in enumerate(device_ids):
        for j, cluster_id in enumerate(cluster_ids):
            ax = axes[i][j]
            images = fetch_images(device_id, cluster_id)
            if images:
                image_stack = np.stack(images, axis=0)
                mean_image = np.mean(image_stack, axis=0).astype(np.uint8)
                ax.imshow(mean_image)
            else:
                ax.imshow(np.zeros((256, 256, 3), dtype=np.uint8))  # Show an empty image if no data
            ax.axis('off')
            if j == 0:  # Label on the left side of each row
                ax.set_ylabel(f'Device {device_id}', rotation=90, size='large',
                              labelpad=15)  # Rotate the label 90 degrees
            if i == 0:  # Title on top of each column
                ax.set_title(f'Cluster {cluster_id}')

    plt.subplots_adjust(wspace=0.1, hspace=0.1)  # Adjust the space between plots
    plt.show()


# List of device IDs to process
device_ids = [4866, 4961, 5555, 5209, 4681, 5158]
cluster_ids = range(10)  # Cluster IDs from 0 to 9

# Call the function to plot images grid
plot_mean_images_grid(device_ids, cluster_ids)
