# Base image with OpenMPI, Flux, and EFA support for AWS on ARM
FROM ghcr.io/converged-computing/flux-openmpi:ubuntu2204-efa-arm

# Set non-interactive frontend for package installations
ENV DEBIAN_FRONTEND=noninteractive

# Set MPI compilers as default C and CXX compilers
ENV CC=mpicc
ENV CXX=mpicxx

# Install build dependencies, clone, build, and install Kripke
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    cmake \
    git && \
    # Clone the Kripke repository from the main branch and its submodules
    # The --recurse-submodules flag is critical to fetch dependencies like BLT
    git clone --recurse-submodules https://github.com/LLNL/Kripke.git /opt/kripke && \
    cd /opt/kripke && \
    # Create a build directory
    mkdir build && cd build && \
    # Configure the build with CMake
    # Enable MPI for multi-node execution and create a release build
    cmake -DENABLE_MPI=ON \
          -DCMAKE_BUILD_TYPE=Release \
          .. && \
    # Compile the application using all available processor cores
    make -j$(nproc) && \
    # Move the executable from the build directory to a system location on the PATH
    mv kripke.exe /usr/local/bin/kripke && \
    # Clean up the source code to reduce image size
    cd / && rm -rf /opt/kripke && \
    # Clean up apt cache
    rm -rf /var/lib/apt/lists/*

# Set the default command to the Kripke help message
CMD ["kripke"]