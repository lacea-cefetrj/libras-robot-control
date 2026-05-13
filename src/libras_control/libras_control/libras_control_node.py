#!/usr/bin/env python3
"""
controle_libras_node.py
=======================
Nó ROS2 unificado — controla o robô por:
  1. Gestos em Libras via câmera (YOLO)
  2. Teclado WASD (prioridade sobre gestos)

Mapeamento Libras → serial (escravo mecanum calibrado):
  A → e (frente)   B → q (trás)
  C → b (esquerda) D → f (direita)   E → s (parar)

Teclado:
  W → e (frente)   S → q (trás)
  A → b (esquerda) D → f (direita)
  Q → l (girar esq) E → r (girar dir)

Keep-alive: reenvia o comando atual a cada 100ms enquanto
gesto/tecla ativo — mantém o watchdog do escravo vivo.
"""

import os
import sys
import tty
import termios
import select
import threading
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String
import cv2
from ultralytics import YOLO
import serial
import numpy as np

_PKG_DIR = os.path.dirname(os.path.realpath(__file__))
DEFAULT_MODEL = os.path.join(_PKG_DIR, "..", "models", "best.pt")

# ── Mapeamentos ──────────────────────────────────────────────
LETRAS_PARA_SERIAL = {
    "A": "e",   # frente
    "B": "q",   # trás
    "C": "b",   # esquerda
    "D": "f",   # direita
    "E": "s",   # parar
}
LETRAS_PARA_NOME = {
    "A": "FRENTE", "B": "TRAS", "C": "ESQUERDA", "D": "DIREITA", "E": "PARAR",
}
TECLA_PARA_CMD = {
    'w': 'e', 's': 'q', 'a': 'b', 'd': 'f', 'q': 'l', 'e': 'r',
}
TECLA_PARA_NOME = {
    'w': 'FRENTE', 's': 'TRAS', 'a': 'ESQUERDA', 'd': 'DIREITA',
    'q': 'GIRAR ESQ', 'e': 'GIRAR DIR',
}
COR_GESTO = {
    "FRENTE":    (0,   0,   220),
    "TRAS":      (0,   200, 0  ),
    "ESQUERDA":  (220, 180, 0  ),
    "DIREITA":   (0,   180, 220),
    "PARAR":     (120, 120, 120),
    "GIRAR ESQ": (200, 0,   200),
    "GIRAR DIR": (200, 0,   200),
}

BANNER = """
╔══════════════════════════════════════════════╗
║   Controle Unificado — Libras + WASD         ║
║                                              ║
║   GESTOS:  A=frente B=trás C=esq D=dir       ║
║   TECLADO: W=frente S=trás A=esq D=dir       ║
║            Q=girar-esq E=girar-dir           ║
║            Ctrl+C = sair                     ║
║                                              ║
║   Teclado tem prioridade sobre gestos        ║
╚══════════════════════════════════════════════╝
"""

KEEPALIVE_S  = 0.1   # reenvia comando a cada 100 ms
TIMEOUT_KBD  = 0.3   # tempo sem tecla para voltar ao modo gestos
LOOP_KBD_S   = 0.05  # 20 Hz loop teclado


class ControladorUnificado(Node):

    def __init__(self):
        super().__init__("controle_libras")

        self.declare_parameter("model_path",        DEFAULT_MODEL)
        self.declare_parameter("camera_device",     "/dev/video0")
        self.declare_parameter("serial_port",       "/dev/ttyUSB1")
        self.declare_parameter("confianca_min",     0.60)
        self.declare_parameter("vel_linear",        0.3)
        self.declare_parameter("vel_angular",       0.8)
        self.declare_parameter("vel_lateral",       0.3)
        self.declare_parameter("frames_tolerancia", 3)

        model_path   = self.get_parameter("model_path").value
        camera_path  = self.get_parameter("camera_device").value
        serial_port  = self.get_parameter("serial_port").value
        self.conf_min          = self.get_parameter("confianca_min").value
        self.vel_lin           = self.get_parameter("vel_linear").value
        self.vel_ang           = self.get_parameter("vel_angular").value
        self.vel_lat           = self.get_parameter("vel_lateral").value
        self.frames_tolerancia = self.get_parameter("frames_tolerancia").value

        try:
            cam_idx = int(''.join(filter(str.isdigit, camera_path)))
        except Exception:
            cam_idx = 0
        self.get_logger().info(f"Câmera: índice {cam_idx}")

        # --- Serial ---
        self.ser = None
        try:
            self.ser = serial.Serial(
                port=serial_port, baudrate=115200,
                timeout=0.1, dsrdtr=False, rtscts=False,
            )
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            self.get_logger().info(f"Serial: {serial_port}. Aguardando ESP32...")
            time.sleep(2.0)
            self.get_logger().info("ESP32 pronto.")
        except Exception as e:
            self.get_logger().error(f"Falha serial {serial_port}: {e}")
            self.get_logger().warn("Sem serial — apenas /cmd_vel")

        # --- YOLO ---
        self.get_logger().info(f"Carregando modelo: {model_path}")
        self.model = YOLO(model_path)
        self.model(np.zeros((320, 320, 3), dtype="uint8"), verbose=False)
        self.get_logger().info("Modelo aquecido.")

        self.pub_cmd   = self.create_publisher(Twist,  "/cmd_vel",      10)
        self.pub_gesto = self.create_publisher(String, "/libras/gesto", 10)

        # --- Câmera ---
        self.camera = cv2.VideoCapture(cam_idx, cv2.CAP_V4L2)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.camera.set(cv2.CAP_PROP_FPS, 30)
        self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not self.camera.isOpened():
            raise RuntimeError(f"Câmera {cam_idx} indisponível")

        # --- Estado ---
        self.frame_atual       = None
        self.lock_frame        = threading.Lock()
        self.frames_sem_detect = 0

        # Comando atual e timestamp do último envio (para keep-alive)
        self.lock_cmd        = threading.Lock()
        self.cmd_atual       = 's'      # comando sendo enviado agora
        self.nome_atual      = 'PARAR'
        self.ultimo_envio    = 0.0      # timestamp do último envio serial

        # Teclado
        self.teclado_ativo    = False
        self.ultimo_tecla_t   = 0.0

        self._rodando = True

        # Threads
        threading.Thread(target=self._loop_captura,  daemon=True).start()
        threading.Thread(target=self._loop_teclado,  daemon=True).start()
        threading.Thread(target=self._loop_keepalive, daemon=True).start()

        # YOLO a 10 Hz
        self.timer = self.create_timer(0.1, self._callback_yolo)

        print(BANNER)

    # ── Thread câmera ────────────────────────────────────────
    def _loop_captura(self):
        while self._rodando:
            ret, frame = self.camera.read()
            if ret:
                with self.lock_frame:
                    self.frame_atual = frame

    # ── Thread keep-alive ────────────────────────────────────
    def _loop_keepalive(self):
        """Reenvia o comando atual a cada KEEPALIVE_S segundos.
        Isso mantém o watchdog do escravo vivo enquanto
        gesto ou tecla estiver ativo."""
        while self._rodando:
            time.sleep(KEEPALIVE_S)
            with self.lock_cmd:
                cmd  = self.cmd_atual
                nome = self.nome_atual
            # Só reenvia se não for stop
            if cmd != 's':
                self._enviar_serial(cmd)
                self._publicar_twist(cmd)

    # ── Thread teclado ───────────────────────────────────────
    def _loop_teclado(self):
        fd  = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setraw(fd)
        try:
            while self._rodando:
                if select.select([sys.stdin], [], [], 0)[0]:
                    ch = sys.stdin.read(1).lower()

                    if ch == '\x03':
                        self._setar_cmd('s', 'PARAR')
                        rclpy.shutdown()
                        break

                    if ch in TECLA_PARA_CMD:
                        cmd  = TECLA_PARA_CMD[ch]
                        nome = TECLA_PARA_NOME[ch]
                        self.teclado_ativo  = True
                        self.ultimo_tecla_t = time.time()
                        self._setar_cmd(cmd, nome)
                        print(f"\r  [TECLADO] {ch.upper()} → {nome}          ")
                    else:
                        self.teclado_ativo  = True
                        self.ultimo_tecla_t = time.time()
                        self._setar_cmd('s', 'PARAR')

                else:
                    if self.teclado_ativo:
                        if time.time() - self.ultimo_tecla_t > TIMEOUT_KBD:
                            self.teclado_ativo = False
                            self._setar_cmd('s', 'PARAR')
                            print(f"\r  [TECLADO] soltou → STOP          ")

                time.sleep(LOOP_KBD_S)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    # ── Callback YOLO ────────────────────────────────────────
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

        # Teclado tem prioridade — gestos não sobrescrevem
        if not self.teclado_ativo:
            if letra is not None and letra in LETRAS_PARA_SERIAL:
                self.frames_sem_detect = 0
                cmd  = LETRAS_PARA_SERIAL[letra]
                nome = LETRAS_PARA_NOME[letra]
                self._setar_cmd(cmd, nome)
                s = String(); s.data = nome
                self.pub_gesto.publish(s)
            else:
                self.frames_sem_detect += 1
                if self.frames_sem_detect >= self.frames_tolerancia:
                    self._setar_cmd('s', 'PARAR')

        # HUD
        annotated = results[0].plot()
        with self.lock_cmd:
            nome_exibir = self.nome_atual
        modo = "TECLADO" if self.teclado_ativo else "GESTOS"
        cor  = COR_GESTO.get(nome_exibir, (200, 200, 200))
        cv2.putText(annotated, f"{letra or '?'} → {nome_exibir}",
                    (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, cor, 2)
        cv2.putText(annotated, f"conf:{conf:.2f}  [{modo}]",
                    (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, cor, 2)
        cv2.imshow("Controle Libras", annotated)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            self._setar_cmd('s', 'PARAR')
            rclpy.shutdown()

    # ── Helpers ──────────────────────────────────────────────
    def _setar_cmd(self, cmd: str, nome: str):
        with self.lock_cmd:
            mudou = (cmd != self.cmd_atual)
            self.cmd_atual  = cmd
            self.nome_atual = nome
        if mudou:
            self._enviar_serial(cmd)
            self._publicar_twist(cmd)

    def _enviar_serial(self, cmd: str):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(cmd.encode('utf-8'))
                self.ser.flush()
            except Exception as e:
                self.get_logger().warn(f"Erro serial: {e}")

    def _publicar_twist(self, cmd: str):
        msg = Twist()
        if   cmd == 'e': msg.linear.x  =  self.vel_lin
        elif cmd == 'q': msg.linear.x  = -self.vel_lin
        elif cmd == 'b': msg.linear.y  =  self.vel_lat
        elif cmd == 'f': msg.linear.y  = -self.vel_lat
        elif cmd == 'l': msg.angular.z =  self.vel_ang
        elif cmd == 'r': msg.angular.z = -self.vel_ang
        self.pub_cmd.publish(msg)

    # ── Destruição ───────────────────────────────────────────
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
    node = ControladorUnificado()
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