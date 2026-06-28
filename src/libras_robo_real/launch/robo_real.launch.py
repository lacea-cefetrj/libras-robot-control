from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([
        Node(package='libras_robo_real', executable='libras_robo_real_node',
             name='libras_robo_real_node', output='screen'),
    ])
