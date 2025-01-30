FROM python:3.12-slim

# Install minimal system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        curl \
        pkg-config \
        libssl-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Rust and base Python setup with optimized settings
ENV PATH="/root/.cargo/bin:${PATH}"
ENV CARGO_NET_GIT_FETCH_WITH_CLI=true
ENV RUST_BACKTRACE=1
ENV RUSTFLAGS="-C target-cpu=native"
ENV CARGO_PROFILE_RELEASE_LTO=true
ENV CARGO_PROFILE_RELEASE_CODEGEN_UNITS=1

# Install minimal Rust toolchain for crypto compilation
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain stable && \
    . $HOME/.cargo/env && \
    pip install --no-cache-dir --upgrade pip setuptools wheel

# Install core dependencies first
RUN pip install --no-cache-dir \
    "loguru>=0.7.0" \
    "python-dotenv>=0.21.0" \
    "requests>=2.32.0" \
    "munch>=2.5.0" \
    "pyyaml>=6.0.1" \
    "prometheus-client>=0.17.1" \
    "numpy<2.0.0" \
    "nest-asyncio>=1.5.0"

# Install scientific packages with minimal dependencies
RUN pip install --no-cache-dir \
    "scipy>=1.12.0" \
    "scikit-learn>=1.5.1" \
    --only-binary=:all:

# Install minimal bittensor components
RUN pip install --no-cache-dir \
    "bittensor>=8.2.0" \
    "masa-ai>=0.2.5" \
    --no-deps && \
    pip install --no-cache-dir \
    "pytest>=7.2.0" \
    "pytest-asyncio>=0.21.0"

# Set up workspace
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CONFIG_PATH=/app/subnet-config.json
ENV ROLE=validator
ENV NETWORK=test
ENV NETUID=165

# Copy startup directory
COPY startup /app/startup

# Set Python path
ENV PYTHONPATH=/app

# Use Python script directly as entrypoint
ENTRYPOINT ["python", "-u", "/app/startup/entrypoint.py"]