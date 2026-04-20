#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import cv2    # OpenCV (webcam e imagem)
import mediapipe as mp  #deteccao de mao

mp_maos = mp.solutions.hands  
mp_desenho = mp.solutions.drawing_utils


def contar_dedos(landmarks_mao, lado: str) -> int:  #funcao responsavel por contar quantos dedos estao levantados
    lm = landmarks_mao.landmark
    PONTAS = [8, 12, 16, 20]
    JUNTAS = [6, 10, 14, 18]
    levantados = 0

    ponta_polegar = lm[4]
    junta_polegar = lm[3]
    if lado == "Right":  #polegar usa uma forma de verificar diferente(questao anatomica)
        if ponta_polegar.x < junta_polegar.x:  
            levantados += 1
    else:
        if ponta_polegar.x > junta_polegar.x:
            levantados += 1

    for ponta, junta in zip(PONTAS, JUNTAS):
        if lm[ponta].y < lm[junta].y:
            levantados += 1

    return levantados


def classificar_gesto(quantidade_dedos: int) -> str:
    if quantidade_dedos == 0:
        return "PARAR"
    elif quantidade_dedos == 1:
        return "ESQUERDA"
    elif quantidade_dedos == 2:
        return "DIREITA"
    elif quantidade_dedos == 3:
        return "FRENTE"
    elif quantidade_dedos >= 4:
        return "TRAS"
    else:
        return "PARAR"


class ControladorGestual(Node):
    """
    Node que controla tudo
    Tem as definicoes de velocidade do robo
    Define a cor do texto na tela
    """

    VELOCIDADE_LINEAR  = 0.5
    VELOCIDADE_ANGULAR = 0.8

    COR_GESTO = {
        "FRENTE":   (0, 0, 220),
        "TRAS":     (0, 220, 0),
        "ESQUERDA": (220, 180, 0),
        "DIREITA":  (0, 180, 220),
        "PARAR":    (120, 120, 120),
    }

    def __init__(self):
        super().__init__("controlador_gestual")
        self.publicador_cmd = self.create_publisher(Twist, "/cmd_vel", 10) #topico: /cmd_vel, mensagem do tipo Twist
        self.temporizador = self.create_timer(1.0 / 30.0, self.callback_temporizador)#atualmente a funcao principal executa 30 vzs por segundo
        self.gesto_atual = "PARAR"

        self.camera = cv2.VideoCapture("/dev/video2", cv2.CAP_V4L2) #estou usando o /dev/video2 mas isso muda de cada sistema, provavelmente deve o /dev/video0 deve funcionar se o 2 nao funcionar
        if not self.camera.isOpened():
            self.get_logger().error("Nao foi possivel abrir a webcam!")
            raise RuntimeError("Webcam nao disponivel")

        self.detector_maos = mp_maos.Hands( #esta configurado para ler no meximo 1 mao
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.6,
        )
        self.get_logger().info("Controlador Gestual iniciado! Pressione 'q' para encerrar.")

    def callback_temporizador(self):
        ret, frame = self.camera.read()
        if not ret:
            self.get_logger().warn("Frame nao capturado.")
            return

        frame = cv2.flip(frame, 1) #espelha a imagem
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) #converte para rgb
        resultado = self.detector_maos.process(rgb) #detecta a mao

        gesto = "PARAR"

        if resultado.multi_hand_landmarks and resultado.multi_handedness:
            for landmarks_mao, info_mao in zip(
                resultado.multi_hand_landmarks, resultado.multi_handedness
            ):
                lado = info_mao.classification[0].label
                mp_desenho.draw_landmarks(frame, landmarks_mao, mp_maos.HAND_CONNECTIONS)
                quantidade_dedos = contar_dedos(landmarks_mao, lado)
                gesto = classificar_gesto(quantidade_dedos)

        self.gesto_atual = gesto
        self.publicar_comando(gesto) #publica o comando ROS

        cor = self.COR_GESTO.get(gesto, (200, 200, 200))
        cv2.putText(
            frame, gesto,
            (10, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.8, cor, 3,
        )

        cv2.imshow("Controle Gestual", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"): #tecla para sair do programa
            self.parar_robo()
            rclpy.shutdown()
 
    def publicar_comando(self, gesto: str): #envio de comnado para o robo
        msg = Twist()
        if gesto == "FRENTE":
            msg.linear.x  = -self.VELOCIDADE_LINEAR
        elif gesto == "TRAS":
            msg.linear.x  =  self.VELOCIDADE_LINEAR
        elif gesto == "ESQUERDA":
            msg.angular.z =  self.VELOCIDADE_ANGULAR
        elif gesto == "DIREITA":
            msg.angular.z = -self.VELOCIDADE_ANGULAR
        self.publicador_cmd.publish(msg)

    def parar_robo(self):
        self.publicador_cmd.publish(Twist())

    def destroy_node(self):
        self.parar_robo()
        self.detector_maos.close()
        self.camera.release()
        cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    no = ControladorGestual()
    try:
        rclpy.spin(no)
    except KeyboardInterrupt:
        pass
    finally:
        no.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()