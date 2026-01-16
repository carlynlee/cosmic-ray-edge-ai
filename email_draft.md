Subject: Update on Cosmic Ray Detection Task

Hi Harvey, Spencer, Wu,

Happy New Year! 

I wanted to provide a quick update on this.  I followed up with Zichun (the author of the RINO paper you shared: https://arxiv.org/abs/2509.07486) on adapting self-supervised learning methods for our CREDO and CosmicWatch data. Based on his recommendations, the approach involves:

1. For CREDO images, using DINO-v2/v3 vision transformers directly (rather than adapting RINO's particle physics framework). Since the images are already in standard format we can likely leverage META's pre-trained models.

2. For CosmicWatch Event Sequences, Zichun suggests using BERT/GPT-style transformers for the time-series event data, treating each event as a token to learn contextual embeddings from the irregularly sampled sequences. I am exploring the BERT/GPT architecture to adapt it for CosmicWatch data.

3. For Multi-Modal Fusion, we might be able to combine both modalities in a unified embedding space for high-confidence event identification and cross-modal validation. I think this would take more time to explore.

I started a rough implementation for foundational modules using each of the two data types and am continuing to explore a pre-training and fine-tuning pipelines. The RINO framework provides useful inspiration, thank you for showing me that. I'm looking to adapt the transformer principles rather than directly using the particle physics approach.

I'll keep you updated as the exploration progresses and if I have any results to share.

Thanks and Happy New Year!

Carlyn

