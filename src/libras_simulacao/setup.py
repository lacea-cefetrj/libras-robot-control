from setuptools import setup
from glob import glob

package_name = 'libras_simulacao'
setup(
    name=package_name, version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.py')),
        ('share/' + package_name + '/urdf',   glob('urdf/*.urdf')),
        ('share/' + package_name + '/models', glob('models/*.pt')),
    ],
    install_requires=['setuptools'], zip_safe=True,
    maintainer='Seu Nome', maintainer_email='seu@email.com',
    description='Simulação do robô tanque no Gazebo via LIBRAS',
    license='MIT',
    entry_points={'console_scripts': [
        'libras_simulacao_node = libras_simulacao.libras_simulacao_node:main',
    ]},
)
