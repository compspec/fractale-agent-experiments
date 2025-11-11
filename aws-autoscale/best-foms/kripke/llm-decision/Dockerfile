# Base image: Ubuntu 22.04 LTS provides a stable and modern userspace for compilation.
FROM ubuntu:22.04

# Set non-interactive frontend for package managers to prevent prompts during build.
ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies in a single layer to optimize image size.
# - build-essential: C/C++ compilers and make.
# - ca-certificates: Required for secure git clone over HTTPS.
# - cmake: Build system generator for Kripke.
# - git: For cloning the source code.
# - openmpi-bin & libopenmpi-dev: Open MPI runtime and development headers for MPI support.
# Apt caches are cleaned in the same layer to reduce final image size.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    cmake \
    git \
    libopenmpi-dev \
    openmpi-bin \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set a temporary working directory for the build process.
# This directory will be removed after the build is complete.
WORKDIR /tmp/build

# Clone, build, and install Kripke in a single RUN layer.
# This minimizes image layers and cleans up all intermediate build artifacts.
# 1. Clone with --recurse-submodules to fetch the BLT dependency.
# 2. FIX: Use the correct branch name 'master' as 'main' does not exist in the remote repository.
# 3. Create a build subdirectory and configure with CMake for a Release build with MPI enabled.
# 4. Compile the application using all available processor cores for a faster build.
# 5. Copy the 'kripke.exe' executable to '/usr/local/bin/kripke' to place it on the PATH.
# 6. Clean up the entire build directory.
RUN git clone --depth 1 --recurse-submodules --branch master https://github.com/LLNL/Kripke.git && \
    cd Kripke && \
    mkdir build && \
    cd build && \
    cmake .. \
        -DENABLE_MPI=ON \
        -DCMAKE_BUILD_TYPE=Release && \
    make -j$(nproc) && \
    cp bin/kripke.exe /usr/local/bin/kripke && \
    cd / && \
    rm -rf /tmp/build

# Reset working directory to a standard location.
WORKDIR /

# Configure Open MPI for containerized/cloud environments.
# This allows mpirun to execute as the root user, a common pattern in Docker containers.
ENV OMPI_ALLOW_RUN_AS_ROOT=1
ENV OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1

# Note for runtime execution:
# In a Kubernetes environment, you may need to explicitly specify the pod network interface for MPI communication, for example:
# mpirun --mca btl_tcp_if_include eth0 -np <processes> kripke [args]

# Set the default command to show Kripke's help message.
# This serves as a basic health check and demonstrates that the executable is on the PATH.
CMD ["kripke", "--help"]