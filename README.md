# Controle Gestual de Robô Diferencial

Controle de robô móvel simulado no Gazebo Classic via gestos de mão captados pela webcam, usando ROS2 Humble, OpenCV e MediaPipe, totalmente containerizado com Docker.

---

## Demonstração

> 📸 *Foto do robô no Gazebo — adicionar aqui*

> 🎥 *Vídeo do sistema funcionando — adicionar aqui*

---

## Gestos

| Gesto | Dedos | Comando |
|-------|-------|---------|
| Punho fechado | 0 | Parar |
| 1 dedo | 1 | Esquerda |
| 2 dedos | 2 | Direita |
| 3 dedos | 3 | Frente |
| Mão aberta | 4+ | Trás |

---

## Requisitos

- Ubuntu 22.04
- Docker + Docker Compose
- Webcam USB
- Placa de vídeo com suporte a OpenGL (para o Gazebo)

> Não é necessário instalar ROS2, MediaPipe ou qualquer dependência — tudo roda dentro do Docker.

---

## Como rodar

### 1. Instale o Docker

```bash
sudo apt install docker.io docker-compose-v2
sudo usermod -aG docker $USER
# Reinicie o terminal após este comando
```

### 2. Clone o repositório

```bash
git clone https://github.com/Lucas-ros4/controle_gestual
cd controle_gestual
```

### 3. Verifique o índice da sua webcam

```bash
v4l2-ctl --list-devices
```

Se sua webcam **não** for `/dev/video2`, edite o arquivo `docker/docker-compose.yml` e troque as duas ocorrências de `/dev/video2` pelo device correto.

### 4. Dê permissão de execução ao nó

```bash
chmod +x src/controle_gestual/controle_gestual/controle_gestual_node.py
```

### 5. Suba o container

```bash
xhost +local:docker
cd docker
docker compose up --build
```

> Na primeira vez o build pode demorar alguns minutos. Nas próximas vezes use apenas `docker compose up`.

### 6. Em outro terminal — abra o Gazebo com o robô

```bash
cd docker
docker compose exec controle_gestual bash
```

Dentro do container:

```bash
source /root/ros2_ws/install/setup.bash
ros2 launch controle_gestual robo.launch.py
```

### 7. Em um terceiro terminal — rode o nó de gestos

```bash
cd docker
docker compose exec controle_gestual bash
```

Dentro do container:

```bash
chmod +x /root/ros2_ws/src/controle_gestual/controle_gestual/controle_gestual_node.py
source /root/ros2_ws/install/setup.bash
ros2 run controle_gestual controle_gestual_node.py
```

---

## Estrutura do projeto
controle_gestual/
├── src/
│   └── controle_gestual/
│       ├── CMakeLists.txt
│       ├── package.xml
│       ├── launch/
│       │   └── robo.launch.py
│       ├── urdf/
│       │   └── my_robot.urdf
│       └── controle_gestual/
│           └── controle_gestual_node.py
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── entrypoint.sh
├── .gitignore
└── README.md

---

## Solução de problemas

**`ros2 run`: No executable found**
```bash
chmod +x /root/ros2_ws/src/controle_gestual/controle_gestual/controle_gestual_node.py
source /root/ros2_ws/install/setup.bash
```

**Gazebo não abre / erro de display**
```bash
xhost +local:docker
```
> Execute este comando no terminal do host antes de subir o container. Deve ser repetido após reiniciar o computador.

**Webcam não encontrada**
```bash
v4l2-ctl --list-devices
# Ajuste o /dev/videoX no docker/docker-compose.yml
```

---

## Tecnologias

- [ROS2 Humble](https://docs.ros.org/en/humble/)
- [Gazebo Classic](https://classic.gazebosim.org/)
- [MediaPipe](https://mediapipe.dev/)
- [OpenCV](https://opencv.org/)
- [Docker](https://www.docker.com/)

---

## Autor

Lucas — [@Lucas-ros4](https://github.com/Lucas-ros4)
