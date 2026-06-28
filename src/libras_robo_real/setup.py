from setuptools import setup
from glob import glob

package_name = 'libras_robo_real'
setup(
    name=package_name, version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.py')),
        ('share/' + package_name + '/models', glob('models/*.pt')),
    ],
    install_requires=['setuptools'], zip_safe=True,
    maintainer='Seu Nome', maintainer_email='seu@email.com',
    description='Controle do robô físico via LIBRAS',
    license='MIT',
    entry_points={'console_scripts': [
        'libras_robo_real_node = libras_robo_real.libras_robo_real_node:main',
    ]},
)
