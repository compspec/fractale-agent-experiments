# Base image with Flux, OpenMPI, and EFA support for ARM on AWS Kubernetes
# This provides a pre-configured environment for multi-node MPI communication.
FROM ghcr.io/converged-computing/flux-openmpi:ubuntu2204-efa-arm

# Set environment variables for the build
ENV OSU_BENCHMARKS_VERSION=7.3
ENV OSU_BENCHMARKS_URL=http://mvapich.cse.ohio-state.edu/download/mvapich/osu-micro-benchmarks-${OSU_BENCHMARKS_VERSION}.tar.gz

# Set the C and C++ compilers to the MPI wrappers provided by the base image.
# This ensures that the OSU Benchmarks are compiled with MPI support.
ENV CC=mpicc
ENV CXX=mpicxx

# Perform system updates, install dependencies, download, build,
# install benchmarks, and clean up all in a single RUN command to minimize layer size.
RUN set -e && \
    # Update package lists and install build dependencies and certificates.
    # --no-install-recommends reduces unnecessary package installation.
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    automake \
    autoconf \
    libtool \
    ca-certificates && \
    \
    # Create a temporary directory for the build process.
    mkdir -p /tmp/build && \
    cd /tmp/build && \
    \
    # Download the OSU Benchmarks source code and extract it.
    # The --strip-components=1 flag removes the top-level directory from the tarball.
    wget -q -O - ${OSU_BENCHMARKS_URL} | tar -xz --strip-components=1 && \
    \
    # Configure the build. The build system will automatically use the
    # compilers specified by the CC and CXX environment variables.
    ./configure && \
    \
    # Compile the source code using all available processor cores.
    make -j$(nproc) && \
    \
    # Find all compiled MPI benchmark executables and copy them to /usr/local/bin,
    # which is in the default system PATH. This makes benchmarks like 'osu_latency'
    # directly available to the user.
    find ./c/mpi -type f -name "osu_*" -executable -exec cp {} /usr/local/bin/ \; && \
    \
    # Clean up to reduce the final image size.
    # Remove the build directory and the apt package cache.
    cd / && \
    rm -rf /tmp/build && \
    rm -rf /var/lib/apt/lists/*

# The container is now ready. The OSU benchmark executables (e.g., osu_latency)
# can be run directly with mpirun or flux.
# Example: mpirun -np 2 osu_latency

