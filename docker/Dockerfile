FROM osrf/ros:humble-desktop

# ── Dependências do sistema ──────────────────────────────────────
RUN apt-get update && apt-get install -y \
    python3-pip \
    ros-humble-gazebo-ros-pkgs \
    ros-humble-robot-state-publisher \
    ros-humble-xacro \
    libgl1-mesa-glx \
    libgl1-mesa-dri \
    v4l-utils \
    && rm -rf /var/lib/apt/lists/*

# ── Dependências Python ──────────────────────────────────────────
RUN pip3 install --no-cache-dir \
    ultralytics \
    opencv-python==4.8.1.78 \
    pyserial \
    "numpy<2"

# ── Copia o workspace ────────────────────────────────────────────
COPY src/ /root/ros2_ws/src/

# ── Entrypoint ───────────────────────────────────────────────────
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
