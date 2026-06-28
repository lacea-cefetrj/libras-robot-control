#!/bin/bash
set -e

ROS_DISTRO="humble"
ROS_WS="/root/ros2_ws"

# Diretório de runtime gráfico
export XDG_RUNTIME_DIR=/tmp/runtime-root
mkdir -p $XDG_RUNTIME_DIR
chmod 700 $XDG_RUNTIME_DIR

# ROS Domain
export ROS_DOMAIN_ID=0
grep -q "export ROS_DOMAIN_ID" /root/.bashrc || \
    echo "export ROS_DOMAIN_ID=0" >> /root/.bashrc

# Source do ROS base
source /opt/ros/$ROS_DISTRO/setup.bash

# Evita que o colcon varra pacotes do sistema
touch /usr/lib/python3/dist-packages/COLCON_IGNORE
touch /usr/local/lib/python3.10/dist-packages/COLCON_IGNORE 2>/dev/null || true

# Limpa builds anteriores para garantir estado limpo
rm -rf $ROS_WS/build $ROS_WS/install $ROS_WS/log

cd $ROS_WS

# Compila os 3 pacotes na ordem correta (modelo primeiro, depois os nós)
colcon build \
    --packages-select \
        libras_modelo_yolo \
        libras_robo_real \
        libras_simulacao \
    --symlink-install \
    --event-handlers console_direct+

# Source do workspace compilado
source $ROS_WS/install/setup.bash

# Persiste o source no bashrc para novos terminais
grep -q "source /opt/ros/humble/setup.bash" /root/.bashrc || \
    echo "source /opt/ros/humble/setup.bash" >> /root/.bashrc

grep -q "source $ROS_WS/install/setup.bash" /root/.bashrc || \
    echo "source $ROS_WS/install/setup.bash" >> /root/.bashrc

exec "$@"
