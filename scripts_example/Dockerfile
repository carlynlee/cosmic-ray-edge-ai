FROM gitlab-registry.nrp-nautilus.io/cloud-ai-100/qaic-docker-images:vllm-latest

# Set working directory
WORKDIR /workspace

# Copy requirements first for better caching
COPY requirements.txt /workspace/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . /workspace/

# Create directories for data
RUN mkdir -p /data/images /data/models /data/exports

# Set environment variables
ENV PYTHONPATH=/workspace
ENV PYTHONUNBUFFERED=1
ENV TF_CPP_MIN_LOG_LEVEL=2

# Expose Jupyter port
EXPOSE 8888

# Default command to start Jupyter
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=''", "--notebook-dir=/workspace"]
