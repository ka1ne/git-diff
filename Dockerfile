FROM python:3.11-slim

# Install git (needed for diff operations)
RUN apt-get update && \
    apt-get install -y git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir semver requests

# Copy the script into the container
COPY generate_template_diff.py /generate_template_diff.py

# Configure git to trust the workspace
RUN git config --global --add safe.directory /github/workspace

# Set the entrypoint
ENTRYPOINT ["python", "/generate_template_diff.py"] 