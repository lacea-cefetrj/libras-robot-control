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

# Limpa build e install antigos antes de compilar
rm -rf $ROS_WS/build $ROS_WS/install $ROS_WS/log

cd $ROS_WS
colcon build

source $ROS_WS/install/setup.bash
cd

source /root/.bashrc
exec "$@"