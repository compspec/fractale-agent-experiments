# Use Ubuntu 22.04 LTS as the base image, a common choice for cloud environments.
FROM ubuntu:22.04

# Set a non-interactive frontend for package managers to avoid prompts during build.
ENV DEBIAN_FRONTEND=noninteractive

# Install essential build tools, dependencies for LAMMPS, and MPI.
# - build-essential, cmake, git: For compiling source code.
# - python3: (FIX) Required by the LAMMPS CMake build system.
# - ca-certificates: For secure git clone over HTTPS.
# - openmpi-bin, libopenmpi-dev: OpenMPI runtime and development libraries.
# - fftw3-dev: FFTW library, a common dependency for performance-critical packages like KSPACE.
# - libgomp1: GNU OpenMP library, explicitly requested.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    python3 \
    ca-certificates \
    openmpi-bin \
    libopenmpi-dev \
    fftw3-dev \
    libgomp1 && \
    rm -rf /var/lib/apt/lists/*

# Configure OpenMPI for container environments.
# These settings allow MPI to run as the root user and specify the network
# interface, which is critical for multi-node communication in Kubernetes.
ENV OMPI_ALLOW_RUN_AS_ROOT=1
ENV OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1
ENV OMPI_MCA_btl_tcp_if_include=eth0
ENV OMPI_MCA_oob_tcp_if_include=eth0

# Set a temporary build directory.
WORKDIR /tmp/build

# Clone the latest stable branch of the LAMMPS source code from GitHub.
# --depth 1 creates a shallow clone, reducing download size.
RUN git clone --depth 1 https://github.com/lammps/lammps.git

# Create a build directory and run CMake to configure the build.
# We enable specific packages required for this application:
# - BUILD_MPI=on: Enable MPI support.
# - PKG_REAXFF=on: Enable the ReaxFF package.
# - PKG_KSPACE=on: Enable the KSPACE package for long-range electrostatics (uses FFTW).
RUN cd lammps && \
    mkdir build && \
    cd build && \
    cmake ../cmake \
      -D BUILD_MPI=on \
      -D PKG_REAXFF=on \
      -D PKG_KSPACE=on

# Compile LAMMPS using all available processor cores.
RUN cd lammps/build && \
    make -j$(nproc)

# Create the final application directory, copy required example files,
# copy the compiled executable to a system PATH location, and clean up sources.
RUN mkdir -p /app && \
    cp /tmp/build/lammps/examples/reaxff/HNS/* /app/ && \
    cp /tmp/build/lammps/build/lmp /usr/local/bin/ && \
    rm -rf /tmp/build

# Set the application directory as the default working directory.
WORKDIR /app

# Set a default command to start a shell. This can be overridden at runtime.
CMD ["/bin/bash"]