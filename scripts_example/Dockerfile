     FROM gitlab-registry.nrp-nautilus.io/cloud-ai-100/qaic-docker-images:vllm-latest
     
     # Copy your code
     COPY . /workspace/
     
     # Install additional requirements
     RUN pip install -r requirements.txt
     
     # Set working directory
     WORKDIR /workspace
