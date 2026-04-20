#!/bin/bash

ROS_DISTRO="humble"
ROS_WS="/root/ros2_ws"

export XDG_RUNTIME_DIR=/tmp/runtime-$USER
mkdir -p $XDG_RUNTIME_DIR
chmod 700 $XDG_RUNTIME_DIR

if ! grep -q "export ROS_DOMAIN_ID" /root/.bashrc; then
    echo "export ROS_DOMAIN_ID=0" >> /root/.bashrc
fi
export ROS_DOMAIN_ID=0

source /opt/ros/$ROS_DISTRO/setup.bash
source /root/.bashrc

# Impede o colcon de varrer pacotes Python do sistema
touch /usr/lib/python3/dist-packages/COLCON_IGNORE
touch /usr/local/lib/python3.10/dist-packages/COLCON_IGNORE 2>/dev/null || true

# Limpa builds antigos
rm -rf $ROS_WS/build $ROS_WS/install $ROS_WS/log

# Compila apenas o pacote do projeto
cd $ROS_WS
colcon build \
    --packages-select controle_gestual \
    --symlink-install \
    --event-handlers console_direct+

source $ROS_WS/install/setup.bash
echo "export ROS_DOMAIN_ID=0" >> /root/.bashrc
source /root/.bashrc

exec "$@"