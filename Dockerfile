FROM ros:humble-ros-base

# Dependências do sistema
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-colcon-common-extensions \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libx11-dev \
    v4l-utils \
    udev \
    && rm -rf /var/lib/apt/lists/*

# Dependências Python (sem --break-system-packages, não precisa dentro do container)
RUN pip3 install \
    ultralytics \
    opencv-python \
    pyserial

# Copia o pacote
WORKDIR /ros2_ws
COPY src/ src/

# Build do pacote
RUN . /opt/ros/humble/setup.sh && \
    colcon build --packages-select libras_control

# Entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
