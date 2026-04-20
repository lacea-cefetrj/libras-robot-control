cmake_minimum_required(VERSION 3.8)
project(controle_gestual)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclpy REQUIRED)

ament_python_install_package(${PROJECT_NAME})

install(PROGRAMS
  controle_gestual/controle_gestual_node.py
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY
  urdf
  launch
  DESTINATION share/${PROJECT_NAME}
)

ament_package()