# Base Image: Ubuntu 22.04 LTS for a stable, well-supported OS
FROM ubuntu:22.04

# Set environment variables to enable non-interactive installation
ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies, MPI, git, certificates, and required runtime libraries
# - build-essential, gfortran, make: For compiling the C/Fortran application
# - git: To clone the source code repository
# - ca-certificates: For secure network communications (e.g., git clone)
# - openmpi-bin, libopenmpi-dev: For compiling and running the MPI application
# - libgomp1: Provides the libgomp.so.1 shared library for OpenMP support
# Clean up apt cache to reduce image size
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    gfortran \
    make \
    git \
    ca-certificates \
    openmpi-bin \
    libopenmpi-dev \
    libgomp1 && \
    rm -rf /var/lib/apt/lists/*

# Create a temporary build directory, clone the source, build, install, and clean up in a single layer
# This optimizes image size by not storing intermediate build artifacts in separate layers
RUN mkdir -p /build && \
    cd /build && \
    git clone https://github.com/LLNL/AMG.git && \
    cd AMG && \
    make && \
    cp test/amg /usr/local/bin/amg && \
    cd / && \
    rm -rf /build

# Configure OpenMPI for containerized environments
# Excludes loopback and default docker bridge interfaces from consideration for MPI traffic,
# which is a common requirement for running MPI in Docker/Kubernetes.
ENV OMPI_MCA_btl_tcp_if_exclude="lo,docker0" \
    OMPI_MCA_oob_tcp_if_exclude="lo,docker0" \
    OMPI_MCA_btl_vader_single_copy_mechanism=none

# Set the default working directory for the container
WORKDIR /

# Define a default command to be executed when the container starts
# This will print the help message for the amg executable
CMD ["amg", "-h"]