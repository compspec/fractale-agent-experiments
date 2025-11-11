# Use a standard Ubuntu base image suitable for AWS CPU instances
FROM ubuntu:22.04

# Avoid interactive prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Install essential build tools, compilers, version control, and Open MPI
# This layer includes ca-certificates for secure network operations
# gfortran is removed as it is not a dependency
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    wget \
    ca-certificates \
    openmpi-bin \
    libopenmpi-dev \
    && rm -rf /var/lib/apt/lists/*

# Configure Open MPI for containerized environments
# These settings improve compatibility and performance in environments like Kubernetes
# Allow running as root, which is common in containers
ENV OMPI_ALLOW_RUN_AS_ROOT=1
ENV OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1
# Disable shared memory mechanisms that can cause issues in some container runtimes
ENV OMPI_MCA_btl_vader_single_copy_mechanism=none
# Exclude InfiniBand and problematic network interfaces
ENV OMPI_MCA_btl="^openib"
ENV OMPI_MCA_btl_tcp_if_exclude="lo,docker0"
# Allow oversubscription of CPU cores, a common practice in HPC/cloud environments
ENV OMPI_MCA_rmaps_base_oversubscribe=1

# Set a temporary directory for building dependencies
WORKDIR /tmp

# Download, build, and install all third-party libraries (TPLs) in a single layer
# This reduces image size and improves build efficiency
RUN \
    # --- METIS 4.0.3 ---
    # Download and extract
    wget --no-check-certificate https://github.com/mfem/tpls/raw/gh-pages/metis-4.0.3.tar.gz && \
    tar -xzvf metis-4.0.3.tar.gz && \
    cd metis-4.0.3 && \
    # Build with specified flags to avoid compiler errors
    make OPTFLAGS="-Wno-error=implicit-function-declaration" && \
    # Manually install METIS as its Makefile lacks an 'install' target
    cp libmetis.a /usr/local/lib/ && \
    cp Lib/metis.h /usr/local/include/ && \
    cd .. && \
    # --- HYPRE 2.28.0 ---
    # Download and extract
    wget --no-check-certificate https://github.com/hypre-space/hypre/archive/refs/tags/v2.28.0.tar.gz && \
    tar -xzvf v2.28.0.tar.gz && \
    cd hypre-2.28.0/src && \
    # Configure with MPI support and required flags
    ./configure --prefix=/usr/local --disable-fortran --enable-bigint CC=mpicc CXX=mpicxx && \
    # Build in parallel
    make -j$(nproc) && \
    # Install to a standard system location
    make install && \
    cd ../.. && \
    # --- MFEM 4.7 ---
    # Clone the repository
    git clone https://github.com/mfem/mfem.git && \
    cd mfem && \
    # Check out the specified version
    git checkout v4.7 && \
    # Build the parallel version, linking against the TPLs we just installed
    make parallel -j$(nproc) MFEM_USE_MPI=YES HYPRE_DIR=/usr/local METIS_DIR=/usr/local && \
    # FIX: Explicitly pass MPI flag to install command to ensure parallel version is installed
    make install MFEM_USE_MPI=YES PREFIX=/usr/local && \
    cd .. && \
    # --- Cleanup ---
    # Remove all source code and archives to keep the final image lean
    rm -rf metis-4.0.3 metis-4.0.3.tar.gz hypre-2.28.0 v2.28.0.tar.gz mfem && \
    # Update the dynamic linker cache to find the newly installed libraries
    ldconfig

# Set the final application working directory
WORKDIR /app

# Clone, build, and install the Laghos application
RUN git clone https://github.com/CEED/Laghos.git && \
    cd Laghos && \
    # Build the application, linking against MFEM
    make -j$(nproc) MFEM_DIR=/usr/local && \
    # Copy the final executable to a directory on the system PATH
    cp laghos /usr/local/bin/ && \
    # Copy the required application data files into the WORKDIR
    cp -r data/* /app/ && \
    cd .. && \
    # Clean up the Laghos source code
    rm -rf Laghos