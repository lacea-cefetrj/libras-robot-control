#!/usr/bin/env python3
"""
libras_gazebo_node.py

Nó ROS2 — controla o robô simulado no Gazebo por gestos em Libras via câmera (YOLO)

Mapeamento Libras:
a -> frente
b -> tras
c -> esquerda
d -> direita
e -> futuramente vai parar
"""

import os
import threading
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String
import cv2
from ultralytics import YOLO
import numpy as np

from ament_index_python.packages import get_package_share_directory
_PKG_DIR = get_package_share_directory("libras_simulacao")
DEFAULT_MODEL = os.path.join(_PKG_DIR, "models", "best.pt")

LETRAS_PARA_NOME = {
    "A": "FRENTE", "B": "TRAS", "C": "ESQUERDA", "D": "DIREITA", "E": "PARAR",
}
COR_GESTO = {
    "FRENTE":   (0,   0,   220),
    "TRAS":     (0,   200, 0  ),
    "ESQUERDA": (220, 180, 0  ),
    "DIREITA":  (0,   180, 220),
    "PARAR":    (120, 120, 120),
}

KEEPALIVE_S = 0.1   # republica comando a cada 100 ms


class ControladorLibrasGazebo(Node):

    def __init__(self):
        super().__init__("libras_gazebo")

        self.declare_parameter("model_path",        DEFAULT_MODEL)
        self.declare_parameter("camera_device",     "/dev/video0")
        self.declare_parameter("confianca_min",     0.60)
        self.declare_parameter("vel_linear",        0.3)
        self.declare_parameter("vel_angular",       0.8)
        self.declare_parameter("frames_tolerancia", 3)

        model_path   = self.get_parameter("model_path").value
        camera_path  = self.get_parameter("camera_device").value
        self.conf_min          = self.get_parameter("confianca_min").value
        self.vel_lin           = self.get_parameter("vel_linear").value
        self.vel_ang           = self.get_parameter("vel_angular").value
        self.frames_tolerancia = self.get_parameter("frames_tolerancia").value

        try:
            cam_idx = int(''.join(filter(str.isdigit, camera_path)))
        except Exception:
            cam_idx = 0
        self.get_logger().info(f"Câmera: índice {cam_idx}")

        self.get_logger().info(f"Carregando modelo: {model_path}")
        self.model = YOLO(model_path)
        self.model(np.zeros((320, 320, 3), dtype="uint8"), verbose=False)
        self.get_logger().info("Modelo aquecido.")

        self.pub_cmd   = self.create_publisher(Twist,  "/cmd_vel",      10)
        self.pub_gesto = self.create_publisher(String, "/libras/gesto", 10)

        self.camera = cv2.VideoCapture(cam_idx, cv2.CAP_V4L2)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.camera.set(cv2.CAP_PROP_FPS, 30)
        self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not self.camera.isOpened():
            raise RuntimeError(f"Câmera {cam_idx} indisponível")

        self.frame_atual       = None
        self.lock_frame        = threading.Lock()
        self.frames_sem_detect = 0

        self.lock_cmd   = threading.Lock()
        self.nome_atual = 'PARAR'

        self._rodando = True

        threading.Thread(target=self._loop_captura,   daemon=True).start()
        threading.Thread(target=self._loop_keepalive, daemon=True).start()

        self.timer = self.create_timer(0.1, self._callback_yolo)

        self.get_logger().info(
            "\n=== Libras Gazebo pronto! ===\n"
            "  A=FRENTE | B=TRAS | C=ESQUERDA | D=DIREITA\n"
            "  Sem sinal = PARADO\n"
            "  Pressione Q na janela para sair."
        )

    def _loop_captura(self):
        while self._rodando:
            ret, frame = self.camera.read()
            if ret:
                with self.lock_frame:
                    self.frame_atual = frame

    def _loop_keepalive(self):
        while self._rodando:
            time.sleep(KEEPALIVE_S)
            with self.lock_cmd:
                nome = self.nome_atual
            if nome != 'PARAR':
                self._publicar_twist(nome)

    def _callback_yolo(self):
        with self.lock_frame:
            if self.frame_atual is None:
                return
            frame = self.frame_atual.copy()

        frame   = cv2.flip(frame, 1)
        results = self.model(frame, conf=self.conf_min, verbose=False, imgsz=320)

        letra = None
        conf  = 0.0
        if len(results[0].boxes) > 0:
            idx   = int(results[0].boxes.conf.argmax())
            cls   = int(results[0].boxes.cls[idx])
            conf  = float(results[0].boxes.conf[idx])
            letra = self.model.names[cls].upper()

        if letra is not None and letra in LETRAS_PARA_NOME:
            self.frames_sem_detect = 0
            nome = LETRAS_PARA_NOME[letra]
            self._setar_nome(nome)
            s = String(); s.data = nome
            self.pub_gesto.publish(s)
        else:
            self.frames_sem_detect += 1
            if self.frames_sem_detect >= self.frames_tolerancia:
                self._setar_nome('PARAR')

        # HUD — caixa do YOLO com a letra
        annotated = results[0].plot()
        cv2.imshow("Libras Gazebo", annotated)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            self._setar_nome('PARAR')
            rclpy.shutdown()

    def _setar_nome(self, nome: str):
        with self.lock_cmd:
            mudou = (nome != self.nome_atual)
            self.nome_atual = nome
        if mudou:
            self._publicar_twist(nome)

    def _publicar_twist(self, nome: str):
        msg = Twist()
        if   nome == 'FRENTE':   msg.linear.x  =  self.vel_lin
        elif nome == 'TRAS':     msg.linear.x  = -self.vel_lin
        elif nome == 'ESQUERDA': msg.angular.z =  self.vel_ang
        elif nome == 'DIREITA':  msg.angular.z = -self.vel_ang
        self.pub_cmd.publish(msg)

    def destroy_node(self):
        self._rodando = False
        self.camera.release()
        cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ControladorLibrasGazebo()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()