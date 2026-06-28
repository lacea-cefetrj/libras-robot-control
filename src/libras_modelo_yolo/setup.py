from setuptools import setup
import os
from glob import glob
package_name = 'libras_modelo_yolo'
setup(
    name=package_name, version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'models'), glob('models/*.pt')),
    ],
    install_requires=['setuptools'], zip_safe=True,
    entry_points={'console_scripts': []},
)
