import sys
from communication import SendFramesClass, RecvFramesClass
from VideoClient import VideoClient

if __name__ == '__main__':

    packetLoss = 0.0
    if len(sys.argv) >= 3:
        if sys.argv[1] in ["-pl", "--packet_loss"]:
            try:
                packetLoss = float(sys.argv[2])
            except Exception:
                pass
            sys.argv.pop(2)
            sys.argv.pop(1)

    # Estos dos segundos de buffer no aportan nada al
    # funcionamiento del buffer. No provoca mayor retardo
    sendThread = SendFramesClass(2, packetLoss)
    # Dos segundos de buffer de recepcion
    recvThread = RecvFramesClass(2)

    # El parámetro usePillow sirve para especificar el uso de 
    # la libreria Pillow para grabar la pantalla.
    # Esta libreria funciona correctamente en Arch, pero no funciona
    # en Ubuntu, por lo que proporcionamos una manera sencilla de alternar 
    # la implementación
    # Si es posible, se recomienda utilizar la librería Pillow 
    # sobre pyscreenshot, ya que proporciona una gran mejora de 
    # rendimiento en el mismo trabajo: capturar la pantalla
    # Por defecto se mantiene en False para asegurar la compatibilidad
    # con otras distribuciones de Linux
    usePillow = False
    vc = VideoClient("1280x900", sendThread, recvThread, usePillow)

    # Lanza el bucle principal del GUI
    # El control ya NO vuelve de esta función, por lo que todas las
    # acciones deberán ser gestionadas desde callbacks y threads
    vc.start()
