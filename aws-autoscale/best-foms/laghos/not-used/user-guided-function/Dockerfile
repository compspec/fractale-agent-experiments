# Use a standard Ubuntu 22.04 base image
FROM ubuntu:22.04

# Set non-interactive frontend for package installations
ENV DEBIAN_FRONTEND=noninteractive

# Define the final application working directory
ENV APP_DIR=/app

# This single RUN command performs all necessary steps in one layer to optimize image size
# within the constraint of a single-stage build. It includes:
# 1. Installing build and runtime dependencies.
# 2. Configuring OpenMPI for containerized environments.
# 3. Downloading and building METIS from source.
# 4. Downloading and building HYPRE from source.
# 5. Downloading and building MFEM from source, linking against METIS and HYPRE.
# 6. Downloading and building the Laghos application against MFEM.
# 7. Copying the final executable and data files to their destination.
# 8. Cleaning up build dependencies and temporary files.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    git \
    wget \
    make \
    ca-certificates \
    openmpi-bin \
    libopenmpi-dev \
    && \
    # Configure OpenMPI for container environments like Docker and Kubernetes.
    # This ensures MPI processes can communicate over the primary virtual network interface.
    echo "btl_tcp_if_include = eth0" >> /etc/openmpi-mca-params.conf && \
    echo "oob_tcp_if_include = eth0" >> /etc/openmpi-mca-params.conf && \
    \
    # --- Build Third-Party Libraries (TPLs) in /tmp ---
    BUILD_DIR=/tmp/build && \
    mkdir -p ${BUILD_DIR} && \
    cd ${BUILD_DIR} && \
    \
    # --- Build METIS 4.0.3 ---
    # METIS is a graph partitioning library required by MFEM.
    # The OPTFLAGS are necessary to avoid build failures with modern GCC versions.
    wget -qO- https://github.com/mfem/tpls/raw/gh-pages/metis-4.0.3.tar.gz | tar -xzf - && \
    cd metis-4.0.3 && \
    make OPTFLAGS="-Wno-error=implicit-function-declaration" && \
    # Manually install library/header as METIS 4.0.3 lacks a 'make install' target.
    cp libmetis.a /usr/local/lib/ && \
    cp Lib/metis.h /usr/local/include/ && \
    cd .. && \
    \
    # --- Build HYPRE 2.28.0 ---
    # HYPRE is a parallel linear solver library required by MFEM.
    # Reverting to a simple in-source build to resolve Makefile generation issues.
    wget -qO- https://github.com/hypre-space/hypre/archive/v2.28.0.tar.gz | tar -xzf - && \
    cd hypre-2.28.0/src && \
    ./configure --prefix=/usr/local --disable-fortran --enable-bigint && \
    make -j$(nproc) && \
    make install && \
    cd ../.. && \
    \
    # --- Build MFEM 4.7 ---
    # MFEM is the finite element library on which Laghos is based.
    # We build the parallel (MPI) version.
    # MFEM_USE_METIS_5=NO is critical when using METIS v4.x.
    git clone --depth 1 --branch v4.7 https://github.com/mfem/mfem.git && \
    cd mfem && \
    # Explicitly point MFEM to dependency locations to ensure a reliable build.
    make parallel -j$(nproc) MFEM_USE_MPI=YES MFEM_USE_METIS_5=NO HYPRE_DIR=/usr/local METIS_DIR=/usr/local && \
    cd .. && \
    \
    # --- Build Laghos ---
    # With all dependencies built, we now compile the main application.
    # We point it to the MFEM build directory.
    git clone https://github.com/CEED/Laghos.git && \
    cd Laghos && \
    make -j$(nproc) MFEM_DIR=${BUILD_DIR}/mfem && \
    \
    # --- Stage Final Artifacts ---
    # Copy the compiled executable to a standard location in the system PATH.
    cp laghos /usr/local/bin/ && \
    # Create the application directory and copy the necessary runtime data files into it.
    mkdir -p ${APP_DIR} && \
    cp -r data/* ${APP_DIR}/ && \
    \
    # --- Cleanup ---
    # Remove the temporary build directory and all build-only dependencies to
    # keep the final container image as small as possible.
    rm -rf ${BUILD_DIR} && \
    apt-get remove -y \
        build-essential \
        g++ \
        git \
        wget \
        make \
        libopenmpi-dev && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Set the final working directory where the application data is located.
# This allows running Laghos with relative paths to its mesh files.
WORKDIR ${APP_DIR}

# The container is now ready. The main executable is 'laghos' on the PATH.
# Example usage:
# docker run <image_name> mpirun -np 4 laghos -p 1 -m cube01_hex.mesh -rs 3 -tf 0.8