# Controle Gestual de Robô Diferencial

Controle de robô móvel simulado no Gazebo Classic via gestos de mão captados pela webcam, usando ROS2 Humble, OpenCV e MediaPipe.

---

## Demonstração

> 📸 *Foto do robô no Gazebo — adicionar aqui*

> 🎥 *Video do sistema funcionando — adicionar aqui*

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
- ROS2 Humble
- Docker + Docker Compose
- Webcam USB

---

## Como rodar

**1. Clone o repositório**
```bash
git clone https://github.com/Lucas-ros4/controle_gestual
cd controle_gestual
```

**2. Suba o container**
```bash
xhost +local:docker
cd docker
docker compose up --build
```

**3. Em outro terminal, rode o nó de gestos**
```bash
docker compose exec controle_gestual bash
ros2 run controle_gestual controle_gestual_node.py
```

---

## Estrutura do projeto
ros2_ws/
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
└── docker/
├── Dockerfile
├── docker-compose.yml
└── entrypoint.sh

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
