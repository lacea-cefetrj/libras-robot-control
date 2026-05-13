from setuptools import setup
import os
from glob import glob

package_name = 'libras_control'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'models'),
            glob('models/*.pt')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='lucas',
    maintainer_email='lucas@example.com',
    description='Controle de robô via gestos LIBRAS',
    license='MIT',
    entry_points={
        'console_scripts': [
            'libras_control_node = libras_control.libras_control_node:main',
        ],
    },
)
