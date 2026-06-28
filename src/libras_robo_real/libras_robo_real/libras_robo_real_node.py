#!/usr/bin/env python3
"""
libras_robo_node.py

Detecta gestos A B C D via YOLO e controla o robô via serial → ESP32.

Mapeamento:
  A -> frente   (manda 'f')
  B -> tras     (manda 'b')
  C -> esquerda (manda 'l')
  D -> direita  (manda 'r')
  
"""

import os
import threading
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import cv2
from ultralytics import YOLO
import serial
import numpy as np
from ament_index_python.packages import get_package_share_directory
_PKG_DIR    = get_package_share_directory("libras_robo_real")
DEFAULT_MODEL = os.path.join(_PKG_DIR, "models", "best.pt")

LETRAS_PARA_CMD = {
    "A": "f", "B": "b", "C": "l", "D": "r",
}
LETRAS_PARA_NOME = {
    "A": "FRENTE", "B": "TRAS", "C": "ESQUERDA", "D": "DIREITA",
}
COR_GESTO = {
    "FRENTE":   (0,   0,   220),
    "TRAS":     (0,   200, 0  ),
    "ESQUERDA": (220, 180, 0  ),
    "DIREITA":  (0,   180, 220),
    "PARADO":   (120, 120, 120),
}

LOOP_ENVIO_MS = 100
YOLO_HZ       = 10


class LibrasRoboNode(Node):

    def __init__(self):
        super().__init__("libras_robo")

        self.i = 0

        self.declare_parameter("model_path",    DEFAULT_MODEL)
        self.declare_parameter("camera_device", "/dev/video0")
        self.declare_parameter("serial_port",   "/dev/ttyUSB0")
        self.declare_parameter("confianca_min", 0.65)
        self.declare_parameter("vel_linear",    0.3)
        self.declare_parameter("vel_lateral",   0.3)

        model_path  = self.get_parameter("model_path").value
        camera_path = self.get_parameter("camera_device").value
        serial_port = self.get_parameter("serial_port").value
        self.conf    = self.get_parameter("confianca_min").value
        self.vel_lin = self.get_parameter("vel_linear").value
        self.vel_lat = self.get_parameter("vel_lateral").value

        try:
            cam_idx = int(''.join(filter(str.isdigit, camera_path)))
        except Exception:
            cam_idx = 0

        # --- Serial ---
        self.ser = None
        try:
            self.ser = serial.Serial(
                port=serial_port, baudrate=115200,
                timeout=0.1, dsrdtr=False, rtscts=False,
            )
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            self.get_logger().info(f"Serial aberta: {serial_port}")
            time.sleep(2.0)
        except Exception as e:
            self.get_logger().error(f"Falha serial: {e}")

        # --- YOLO ---
        self.get_logger().info(f"Carregando modelo: {model_path}")
        self.model = YOLO(model_path)
        self.model(np.zeros((320, 320, 3), dtype="uint8"), verbose=False)
        self.get_logger().info("Modelo pronto.")

        self.pub = self.create_publisher(Twist, "/cmd_vel", 10)

        # --- Câmera ---
        self.camera = cv2.VideoCapture(cam_idx, cv2.CAP_V4L2)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.camera.set(cv2.CAP_PROP_FPS, 30)
        self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # --- Estado ---
        self.frame_bruto  = None
        self.lock_bruto   = threading.Lock()
        self.frame_exibir = None
        self.lock_exibir  = threading.Lock()
        self.lock_cmd     = threading.Lock()
        self.cmd_atual    = 's'
        self._rodando     = True

        threading.Thread(target=self._loop_captura,  daemon=True).start()
        threading.Thread(target=self._loop_yolo,     daemon=True).start()
        threading.Thread(target=self._loop_exibicao, daemon=True).start()
        threading.Thread(target=self._loop_envio,    daemon=True).start()

        self.get_logger().info(
            "\n=== Libras Robo pronto! ===\n"
            "  A=FRENTE | B=TRAS | C=ESQUERDA | D=DIREITA\n"
            "  Sem sinal = PARADO\n"
            "  Pressione Q na janela para sair."
        )

    def _loop_captura(self):
        while self._rodando:
            ret, frame = self.camera.read()
            if ret:
                with self.lock_bruto:
                    self.frame_bruto = frame

    def _loop_yolo(self):
        intervalo = 1.0 / YOLO_HZ
        while self._rodando:
            t0 = time.time()

            with self.lock_bruto:
                if self.frame_bruto is None:
                    time.sleep(intervalo)
                    continue
                frame = self.frame_bruto.copy()

            frame   = cv2.flip(frame, 1)
            
            if self.i % 5 == 0:
                results = self.model(frame, conf=self.conf, verbose=False, imgsz=320)

            letra = None
            conf  = 0.0

            if results is not None:
                if len(results[0].boxes) > 0:
                    idx   = int(results[0].boxes.conf.argmax())
                    cls   = int(results[0].boxes.cls[idx])
                    conf  = float(results[0].boxes.conf[idx])
                    letra = self.model.names[cls].upper()

                novo_cmd = LETRAS_PARA_CMD.get(letra, 's')
                if novo_cmd == 's':
                    letra = None

                with self.lock_cmd:
                    mudou = (novo_cmd != self.cmd_atual)
                    self.cmd_atual = novo_cmd

                if mudou:
                    nome = LETRAS_PARA_NOME.get(letra, "PARADO") if letra else "PARADO"
                    self.get_logger().info(f"{letra or '-'} -> {nome}")

                annotated   = results[0].plot()
                nome_exibir = LETRAS_PARA_NOME.get(letra, "PARADO") if letra else "PARADO"
                cor = COR_GESTO.get(nome_exibir, (120, 120, 120))
                cv2.putText(annotated, f"{letra or '-'} -> {nome_exibir}",
                            (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, cor, 2)
                cv2.putText(annotated, f"conf: {conf:.2f}",
                            (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, cor, 2)

                with self.lock_exibir:
                    self.frame_exibir = annotated

                elapsed = time.time() - t0
                sleep   = intervalo - elapsed
                if sleep > 0:
                    time.sleep(sleep)

    def _loop_exibicao(self):
        while self._rodando:
            with self.lock_exibir:
                frame = self.frame_exibir
            if frame is None:
                with self.lock_bruto:
                    frame = self.frame_bruto
                if frame is not None:
                    frame = cv2.flip(frame.copy(), 1)

            if frame is not None:
                cv2.imshow("Libras Robo", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                self._rodando = False
                rclpy.shutdown()
                break

            time.sleep(1.0 / 30.0)

    def _loop_envio(self):
        while self._rodando:
            with self.lock_cmd:
                cmd = self.cmd_atual
            self._enviar(cmd)
            time.sleep(LOOP_ENVIO_MS / 1000.0)

    def _enviar(self, cmd: str):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(cmd.encode('utf-8'))
                self.ser.flush()
            except Exception:
                pass

        msg = Twist()
        if   cmd == 'f': msg.linear.x =  self.vel_lin
        elif cmd == 'b': msg.linear.x = -self.vel_lin
        elif cmd == 'l': msg.linear.y =  self.vel_lat
        elif cmd == 'r': msg.linear.y = -self.vel_lat
        self.pub.publish(msg)

    def destroy_node(self):
        self._rodando = False
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(b's')
                self.ser.flush()
                self.ser.close()
            except Exception:
                pass
        self.camera.release()
        cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = LibrasRoboNode()
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
