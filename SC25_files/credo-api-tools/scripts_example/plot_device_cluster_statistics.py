
import base64
from io import BytesIO
from PIL import Image

import matplotlib.pyplot as plt
import collections
from elasticsearch import Elasticsearch

# Initialize Elasticsearch client
es = Elasticsearch()

# Expanded list of device IDs
device_ids = [4866, 4961, 5555, 5209, 4681, 5158]

# Function to fetch cluster statistics for each device
def fetch_cluster_stats(device_id):
    query = {
        "query": {
            "bool": {
                "must": [
                    {"term": {"device_id": device_id}},
                    {"range": {"timestamp": {"gte": "2018-10-01T00:00:00", "lte": "2018-10-31T23:59:59"}}},
                    {"exists": {"field": "cluster"}}
                ]
            }
        },
        "size": 1000  # Adjust based on expected number of hits
    }
    resp = es.search(index="credo-detections", body=query)
    return [hit['_source']['cluster'] for hit in resp['hits']['hits'] if 'cluster' in hit['_source']]

# Prepare figure for plotting
f = plt.figure(figsize=(18, 10))  # Adjusted figure size for better visibility
f.suptitle('October 2018: Cluster ID Counts for Top Ranking Device IDs (1000 samples per device)')

# Loop over each device and plot cluster distribution
for i, device_id in enumerate(device_ids):
    clusters = fetch_cluster_stats(device_id)
    plot_data = collections.Counter(clusters)  # Use Counter to simplify counting

    plt.subplot(2, 3, i + 1)  # Adjusted layout for 6 plots
    plt.title(f'Device {device_id}')

    # Creating bar plot for each cluster
    # Ensure x-ticks are set correctly
    plt.bar(range(10), [plot_data[j] for j in range(10)], color='skyblue', alpha=0.7, label='Cluster counts')
    plt.xticks(range(10))  # Set x-ticks to be exactly the cluster IDs
    plt.xlabel('Cluster ID')
    plt.ylabel('Count')
    plt.legend()

plt.tight_layout()
plt.show()


