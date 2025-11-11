# Use the specified ARM64 base image with OpenMPI, Flux, and EFA support
FROM ghcr.io/converged-computing/flux-openmpi:ubuntu2204-efa-arm

# Set environment variables for non-interactive installation
ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies for LAMMPS
# ca-certificates is included for git to function correctly
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Set a temporary build directory
WORKDIR /build

# Clone the latest stable branch of the LAMMPS source code
# Using --depth 1 for a shallow clone to save space and time
RUN git clone -b stable --depth 1 https://github.com/lammps/lammps.git

# Create a build directory and configure LAMMPS using CMake
# Enable the REAXFF package and specify the MPI C and CXX compilers
RUN cd lammps && \
    mkdir build && \
    cd build && \
    cmake ../cmake \
    -D CMAKE_BUILD_TYPE=Release \
    -D BUILD_MPI=yes \
    -D CMAKE_C_COMPILER=mpicc \
    -D CMAKE_CXX_COMPILER=mpicxx \
    -D PKG_REAXFF=on && \
    make -j$(nproc)

# Copy the compiled LAMMPS executable to a location in the system's PATH
# This avoids using symlinks as requested
RUN cp /build/lammps/build/lmp /usr/local/bin/

# Verify that the 'lmp' executable is found in the PATH
RUN which lmp

# Set the final working directory for running the application
WORKDIR /opt/lammps-reax

# Copy the example files for the HNS ReaxFF benchmark into the WORKDIR
RUN cp /build/lammps/examples/reaxff/HNS/* .

# Clean up the build directory to reduce the final image size
RUN rm -rf /build

# Set a default command to start a shell
CMD ["/bin/bash"]