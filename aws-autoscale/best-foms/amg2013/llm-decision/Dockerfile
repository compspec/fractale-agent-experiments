# Base image: Ubuntu 22.04 LTS for a stable, well-supported environment
FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Configure OpenMPI for containerized environments (e.g., Kubernetes)
# These settings ensure compatibility by using TCP for communication and allowing root execution.
ENV OMPI_ALLOW_RUN_AS_ROOT=1
ENV OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1
ENV OMPI_MCA_btl_vader_single_copy_mechanism=none
ENV OMPI_MCA_btl=tcp,self,vader
ENV OMPI_MCA_pml=ob1

# Install dependencies, clone, build, and clean up in a single RUN layer to minimize image size.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    git \
    gfortran \
    openmpi-bin \
    libopenmpi-dev && \
    # Clone the latest default branch of the AMG repository
    git clone https://github.com/LLNL/AMG.git /opt/amg-src && \
    # FIX: First, build the required libraries from the source root directory.
    # This resolves the linker errors from the previous failed build.
    cd /opt/amg-src && make && \
    # Now, build the main amg executable in the 'test' directory.
    cd test && make amg && \
    # Copy the final executable to a system location on the PATH for easy access.
    cp amg /usr/local/bin/amg && \
    # Clean up source code and apt cache to reduce final image size.
    cd / && \
    rm -rf /opt/amg-src && \
    rm -rf /var/lib/apt/lists/*

# Set the default command to the application's help message.
CMD ["amg", "--help"]