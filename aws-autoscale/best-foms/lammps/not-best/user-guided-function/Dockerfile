# Base image: Ubuntu 22.04 for a stable and well-supported environment
FROM ubuntu:22.04

# Set non-interactive installation to prevent prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies, MPI, certificates, and other required libraries
# - build-essential, cmake, g++, gfortran: For compiling C++/Fortran code.
# - git: To clone the LAMMPS source code.
# - openmpi-bin, libopenmpi-dev: OpenMPI for parallel processing.
# - ca-certificates: For secure network communications (e.g., git clone).
# - libgomp1: GNU OpenMP library, required for multi-threading support.
# - python3: [FIX] Added as a required dependency for the LAMMPS build system (cmake).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    g++ \
    gfortran \
    openmpi-bin \
    libopenmpi-dev \
    ca-certificates \
    libgomp1 \
    python3 \
    # Clean up apt cache to reduce image size
    && rm -rf /var/lib/apt/lists/*

# Set OpenMPI environment variables to allow running as root in containerized environments like Kubernetes
ENV OMPI_ALLOW_RUN_AS_ROOT=1
ENV OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1

# Clone the latest branch of LAMMPS, build it with REAXFF, MPI, and OpenMP packages,
# and install the executable.
RUN git clone --depth 1 https://github.com/lammps/lammps.git /lammps && \
    cd /lammps && \
    mkdir build && \
    cd build && \
    cmake \
      -D PKG_REAXFF=on \
      -D BUILD_MPI=yes \
      -D BUILD_OMP=yes \
      ../cmake && \
    make -j$(nproc) && \
    # Copy the main LAMMPS executable to a location on the system PATH
    cp ./lmp /usr/local/bin/

# Set a default working directory for the container
WORKDIR /data

# Copy the example files for the reaxff/HNS benchmark into the working directory
# and then clean up the source code to minimize final image size.
RUN cp /lammps/examples/reaxff/HNS/* /data/ && \
    rm -rf /lammps

# Set the default entrypoint to the LAMMPS executable
ENTRYPOINT ["lmp"]