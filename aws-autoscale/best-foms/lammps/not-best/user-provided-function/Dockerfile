# Base image: Ubuntu 22.04 LTS for a stable, well-supported environment
FROM ubuntu:22.04

# Set environment variables to enable non-interactive installation
ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies, MPI, and required libraries
# ca-certificates is included for secure network operations (e.g., git clone)
# libgomp1 is the GNU OpenMP runtime library, a common dependency for parallel codes
# FIX: Added python3 as it is a required dependency for the LAMMPS cmake build system
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    wget \
    ca-certificates \
    python3 \
    openmpi-bin \
    libopenmpi-dev \
    libfftw3-dev \
    libgomp1 && \
    rm -rf /var/lib/apt/lists/*

# Clone the latest branch of the LAMMPS source code into a temporary directory
# A shallow clone (--depth 1) is used to reduce image size
RUN git clone --depth 1 https://github.com/lammps/lammps.git /tmp/lammps-src

# Configure, build, and install LAMMPS from source
# The build is configured to include the required REAXFF package and MPI support
# KSPACE is also included as it's commonly used with FFTW
RUN cd /tmp/lammps-src && \
    mkdir build && \
    cd build && \
    cmake ../cmake \
        -D CMAKE_BUILD_TYPE=Release \
        -D BUILD_MPI=yes \
        -D PKG_REAXFF=yes \
        -D PKG_KSPACE=yes && \
    make -j$(nproc)

# Copy the main LAMMPS executable to a system location on the PATH
# This makes 'lmp' directly available to users and scripts
RUN cp /tmp/lammps-src/build/lmp /usr/local/bin/

# Set OpenMPI runtime parameters for better compatibility in containerized environments
# This helps prevent common errors when running MPI applications inside containers
ENV OMPI_MCA_btl_vader_single_copy_mechanism=none \
    OMPI_MCA_btl_tcp_if_exclude=lo,docker0 \
    OMPI_MCA_orte_base_help_aggregate=0

# Create a final working directory for the application
WORKDIR /app

# Copy the specific example files into the working directory
RUN cp /tmp/lammps-src/examples/reaxff/HNS/* .

# Clean up the temporary source code directory to minimize final image size
RUN rm -rf /tmp/lammps-src

# Set the final working directory for the container's entrypoint
WORKDIR /app