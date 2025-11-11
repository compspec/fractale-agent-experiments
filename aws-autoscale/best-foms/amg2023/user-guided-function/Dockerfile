# Base image for a CPU environment
FROM ubuntu:22.04

# Set environment variables to enable non-interactive installation
ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies, MPI, git, certificates, and required runtime libraries
# libgomp1 is explicitly installed as requested
# Using --no-install-recommends to keep the image size smaller
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    gfortran \
    git \
    make \
    libopenmpi-dev \
    openmpi-bin \
    libgomp1 && \
    # Clean up apt cache to reduce image size
    rm -rf /var/lib/apt/lists/*

# Configure OpenMPI for containerized/cloud environments
# - Exclude loopback and docker network interfaces to force communication over the primary network
# - Allow oversubscription of CPU cores, which is common in virtualized environments like Kubernetes
RUN echo "btl_tcp_if_exclude = lo,docker0" >> /etc/openmpi-mca-params.conf && \
    echo "rmaps_base_oversubscribe = 1" >> /etc/openmpi-mca-params.conf

# Clone the latest branch of the amg2023 repository, build it,
# copy the executable to the system PATH, and clean up the source code.
RUN git clone https://github.com/llnl/amg.git /opt/amg2023-src && \
    cd /opt/amg2023-src && \
    make && \
    cp test/amg /usr/local/bin/amg && \
    cd / && \
    rm -rf /opt/amg2023-src

# Set a default command for the container.
# Running `amg` without arguments typically shows its usage information.
CMD ["amg"]