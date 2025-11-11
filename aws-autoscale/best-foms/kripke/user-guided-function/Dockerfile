# Base Image: Ubuntu 22.04 LTS
# Provides a stable, modern OS environment for building and running the application.
FROM ubuntu:22.04

# Set non-interactive frontend for package installations to prevent interactive prompts.
ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies, MPI, git, certificates, and an updated version of CMake.
# The Kripke build system requires CMake >= 3.23, which is newer than the version in the
# default Ubuntu 22.04 repositories. The official Kitware APT repository is added to
# install a compatible version.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    git \
    gpg \
    libopenmpi-dev \
    openmpi-bin \
    wget \
    && wget -O - https://apt.kitware.com/keys/kitware-archive-latest.asc | gpg --dearmor -o /usr/share/keyrings/kitware-archive-keyring.gpg \
    && echo 'deb [signed-by=/usr/share/keyrings/kitware-archive-keyring.gpg] https://apt.kitware.com/ubuntu/ jammy main' > /etc/apt/sources.list.d/kitware.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends cmake \
    && rm -rf /var/lib/apt/lists/*

# Configure Open MPI environment variables for containerized execution in Kubernetes.
# This configuration forces TCP communication over the pod's primary network interface (eth0)
# and explicitly allows MPI processes to be run by the root user, per requirements.
ENV OMPI_MCA_btl=tcp,self
ENV OMPI_MCA_btl_tcp_if_include=eth0
ENV OMPI_ALLOW_RUN_AS_ROOT=1
ENV OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1

# Clone the Kripke source code from its main branch and build it.
# This entire process is done in a single RUN instruction to optimize layer usage.
# 1. Clone the repository recursively to fetch required submodules.
# 2. Create a build directory to keep the source tree clean.
# 3. Configure the build with CMake, explicitly setting MPI wrappers (mpicc/mpicxx)
#    to ensure the compiler can find MPI headers (e.g., mpi.h) and libraries.
# 4. Compile the application serially to avoid out-of-memory errors on build systems.
# 5. Install the compiled executable using the standard 'make install' target.
# 6. Clean up the source and build directories to minimize the final image size.
RUN git clone --recursive https://github.com/LLNL/Kripke.git /tmp/kripke && \
    mkdir /tmp/kripke/build && \
    cd /tmp/kripke/build && \
    cmake \
    -D CMAKE_BUILD_TYPE=Release \
    -D CMAKE_INSTALL_PREFIX=/usr/local \
    -D KRIPKE_USE_MPI=ON \
    -D CMAKE_C_COMPILER=mpicc \
    -D CMAKE_CXX_COMPILER=mpicxx \
    .. && \
    make && \
    make install && \
    rm -rf /tmp/kripke

# Set a default working directory for the container.
WORKDIR /data