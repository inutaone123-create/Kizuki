FROM ubuntu:22.04

# タイムゾーン設定
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Tokyo

# 基本パッケージ
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv \
    octave octave-signal \
    liboctave-dev \
    build-essential cmake gdb \
    wget apt-transport-https \
    git curl vim nano \
    zsh sudo \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Rust（rustup経由でインストール — aptより最新かつクロスコンパイル対応）
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
ENV PATH="/root/.cargo/bin:${PATH}"

# Node.js インストール（Claude Code用）
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Claude Code インストール
RUN npm install -g @anthropic-ai/claude-code

# .NET SDK 8.0
RUN wget https://packages.microsoft.com/config/ubuntu/22.04/packages-microsoft-prod.deb -O packages-microsoft-prod.deb && \
    dpkg -i packages-microsoft-prod.deb && \
    rm packages-microsoft-prod.deb && \
    apt-get update && \
    apt-get install -y dotnet-sdk-8.0 && \
    rm -rf /var/lib/apt/lists/*

# Python パッケージ（必要に応じて追加・削除）
RUN pip3 install \
    numpy>=1.21.0 \
    scipy>=1.7.0 \
    matplotlib>=3.4.0 \
    pytest>=7.0.0 \
    pytest-cov>=3.0.0 \
    behave>=1.2.6 \
    black>=23.0.0 \
    ipython \
    sphinx>=7.0.0 \
    sphinx-rtd-theme>=1.3.0 \
    breathe>=4.35.0

# ドキュメント生成ツール（Doxygen + Graphviz）
RUN apt-get update && apt-get install -y \
    doxygen \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

# Octave パッケージ（不要なら削除）
RUN octave --eval "pkg install -forge signal"

# C++ Eigen ライブラリ（不要なら削除）
RUN apt-get update && apt-get install -y \
    libeigen3-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

CMD ["sleep", "infinity"]
