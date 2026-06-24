# Projeto Lucas Leonardo Rosa - WRE

Classificador de LIBRAS para Controle de Robô Móvel

Sistema robótico educacional focado em acessibilidade, capaz de classificar sinais de LIBRAS em tempo real via visão computacional (YOLO) e converter as predições em comandos cinemáticos para um robô móvel integrado ao ecossistema ROS 2 Humble, simulado no Gazebo Classic e replicado no hardware real com ESP32.

---

## Demonstração

### Vídeo

Assista ao vídeo do projeto em funcionamento no YouTube:

[https://www.youtube.com/watch?v=OtmA4iEpjC8](https://www.youtube.com/watch?v=OtmA4iEpjC8)

### Fotos do Hardware

<img width="1600" height="1200" alt="WhatsApp Image 2026-06-24 at 20 04 07" src="https://github.com/user-attachments/assets/5dd5d20f-8d92-4a01-95f1-4411a5bcbfe3" />




### Modelo 3D do Robô

https://www.thingiverse.com/thing:7374425
<img width="1366" height="762" alt="Screenshot_1" src="https://github.com/user-attachments/assets/cc0ec1cc-64f7-444c-8047-54a1d786cbfc" />

---

## Como Funciona o Projeto

O fluxo de funcionamento do sistema é dividido em três camadas principais:

**Camada de Visão (YOLO)**
A webcam captura o usuário executando os sinais de LIBRAS. Um modelo customizado, treinado com YOLO, processa as imagens em tempo real e classifica o gesto correspondente.

**Camada de Software (ROS 2 Humble)**
O nó de visão processa a predição do modelo e converte o resultado em comandos de velocidade (geometry_msgs/Twist). Esses comandos podem ser usados de duas formas, em etapas separadas:

- **Simulação:** movimentam o modelo virtual do robô (descrito em URDF) dentro do ambiente Gazebo Classic.
- **Robô real:** são enviados via porta serial para o microcontrolador ESP32 Mestre.

**Camada de Hardware (ESP32)**
No modo robô real, o ESP32 Mestre recebe os comandos via serial e os retransmite por comunicação sem fio (ESP-NOW) para o ESP32-S3 Escravo embarcado no veículo físico. O robô real replica os movimentos através dos motores, controlados por um driver de ponte H.

---

## Mapeamento de Sinais e Comandos

A tabela abaixo descreve a relação entre o sinal de LIBRAS reconhecido pela câmera e o respectivo comando executado pelo robô:

| Sinal LIBRAS | Comando  |
|--------------|----------|
| A            | Frente   |
| B            | Trás     |
| C            | Direita  |
| D            | Esquerda |

---

## Modelo Treinado (YOLO)

Os pesos gerados após o treinamento do modelo customizado para reconhecimento dos sinais de LIBRAS estão disponíveis em `models/best.pt`, dentro do pacote `libras_robo`. O arquivo contém a rede calibrada para realizar as inferências em tempo real no nó do ROS 2.

---

## Requisitos do Sistema

- Host: Ubuntu 22.04 LTS
- Ambiente: ROS 2 Humble (via container Docker)
- Simulador: Gazebo Classic
- Hardware Host: Webcam USB
- Hardware Embarcado (modo robô real): ESP32 (Mestre) + ESP32-S3 (Escravo) + Driver de motor

---

## Como Rodar o Projeto

### 1. Pré-requisitos

Instale o git:

```bash
sudo apt install git
```

Instale o Docker:

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
```

### 2. Clone o repositório

```bash
git clone git@github.com:lacea-cefetrj/libras-robot-control.git
cd libras-robot-control
```

### 3. Verifique sua webcam

```bash
v4l2-ctl --list-devices
```

Se sua webcam não for `/dev/video2`, edite o `docker/docker-compose.yml` e ajuste o caminho.

### 4. Construa a imagem Docker

Este comando vai baixar o Ubuntu, o ROS 2, o Gazebo e as bibliotecas de visão computacional. Pode demorar alguns minutos na primeira vez.

```bash
cd docker
docker compose build
```

### 5. Dê permissão para abrir telas gráficas

```bash
xhost +local:docker
```

### 6. Suba o container

```bash
docker compose up -d
```

### 7. Entre no container e compile o workspace

```bash
docker compose exec ros2_ws bash
```

Dentro do container:

```bash
source /opt/ros/humble/setup.bash
cd /root/ros2_ws
colcon build
source install/setup.bash
```

### 8. Abrir o Docker depois de já instalado

Sempre que for abrir o container depois do primeiro build, rode:

```bash
cd docker
docker compose up -d
docker compose exec ros2_ws bash
```

Dentro do container, lembre de carregar o ambiente novamente em cada novo terminal:

```bash
source /opt/ros/humble/setup.bash
source /root/ros2_ws/install/setup.bash
```

---

## Atividade 1: Ligar a Simulação (Gazebo)

Com o container aberto e o ambiente carregado, lance o robô no Gazebo:

```bash
ros2 launch controle_gestual robo.launch.py
```

Em um novo terminal, entre no container de novo e rode o nó de controle:

```bash
docker compose exec ros2_ws bash
source /opt/ros/humble/setup.bash
source /root/ros2_ws/install/setup.bash
ros2 run controle_gestual controle_gestual_node.py
```

### Listar os tópicos ativos

```bash
ros2 topic list -t
```

### Conferir mensagens chegando no tópico

```bash
ros2 topic echo /cmd_vel
```

---

## Atividade 2: Controle do Robô Real (LIBRAS + ESP32)

Conecte o ESP32 Mestre via USB e identifique a porta serial:

```bash
ls /dev/ttyUSB*
```

Dentro do container, rode o nó de classificação de LIBRAS:

```bash
ros2 run libras_robo libras_robo_node \
  --ros-args \
  -p camera_device:=/dev/video0 \
  -p serial_port:=/dev/ttyUSB0
```

Uma janela vai abrir mostrando a webcam com o sinal de LIBRAS detectado em tempo real. Faça os sinais da tabela acima para mover o robô físico.

---

## Estrutura do Projeto
