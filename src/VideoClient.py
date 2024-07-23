import numpy as np
import cv2
import time
import datetime
from appJar import gui
from PIL import Image, ImageTk, ImageGrab
import pyscreenshot as pssh
from utils import SUPPORTED_VIDEO_FILES
from apicontrol import *
from apids import *
from utils import TCPUtil
from threading import Thread
from socket import inet_aton


class VideoClient(object):

    def __init__(
            self,
            window_size,
            sendBufClass,
            recvBufClass,
            usePillow=True):

        if usePillow:
            self.screenCapture = ImageGrab
        else:
            self.screenCapture = pssh
        self.colors = {
            'bg': '#909090',
            'fg': '#000000',
            'entry_bg': '#4c4c4c',
            'entry_fg': '#fafafa',
            'button_bg': '#d0d0d0',
        }

        # Buffers de envío y recepción de datos
        # La openCV interactúa con estos buffers
        self.sendBuf = sendBufClass.buf
        self.sendBufClass = sendBufClass
        self.recvBuf = recvBufClass.buf
        self.recvBufClass = recvBufClass

        self.maxWidthBig = 720
        self.heightBig = int(self.maxWidthBig * 9 / 16)
        self.maxWidthSmall = 150

        # Creamos una variable que contenga el GUI principal
        self.app = gui("Redes2 - P2P", window_size)
        self.app.setBg(self.colors['bg'], override=True)
        self.app.setFg(self.colors['fg'], override=True)
        self.app.setGuiPadding(10, 10)
        self.app.setFont(13)
        self.app.setStopFunction(self.checkStop)

        with self.app.subWindow("Registro", modal=True, blocking=True):
            self.app.setStopFunction(self.app.stop)
            self.app.setBg(self.colors['bg'], override=True)
            self.app.setFg(self.colors['fg'], override=True)
            with self.app.labelFrame("Información de registro"):
                self.app.setSticky("ew")
                self.app.setPadding([5, 5])

                self.app.addLabel("l1", "Nickname", 0, 0)
                self.app.addEntry("Nickname", 0, 1)
                self.app.setEntryDefault("Nickname", "Nick")

                self.app.addLabel("l2", "Contraseña", 1, 0)
                self.app.addSecretEntry("Contraseña", 1, 1)
                self.app.setEntryDefault("Contraseña", "********")

                self.app.addLabel("l3", "IP", 2, 0)
                self.app.addEntry("IP", 2, 1)
                self.app.setEntryDefault("IP", "127.0.0.1")

                self.app.addLabel("l4", "Puerto de control", 3, 0)
                self.app.addEntry("Puerto de control", 3, 1)
                self.app.setEntryDefault("Puerto de control", "8080")

                self.app.addLabel("l5", "Puerto de datos", 4, 0)
                self.app.addEntry("Puerto de datos", 4, 1)
                self.app.setEntryDefault("Puerto de datos", "8080")

                self.app.addButtons(["Registrarme", "Cerrar"],
                                    self.registroCallback, 5, 0, 2)

                self.app.setEntryBg("Nickname", self.colors['entry_bg'])
                self.app.setEntryFg("Nickname", self.colors['entry_fg'])
                self.app.setEntryBg("Contraseña", self.colors['entry_bg'])
                self.app.setEntryFg("Contraseña", self.colors['entry_fg'])
                self.app.setEntryBg("IP", self.colors['entry_bg'])
                self.app.setEntryFg("IP", self.colors['entry_fg'])
                self.app.setEntryBg(
                    "Puerto de control",
                    self.colors['entry_bg'])
                self.app.setEntryFg(
                    "Puerto de control",
                    self.colors['entry_fg'])
                self.app.setEntryBg(
                    "Puerto de datos",
                    self.colors['entry_bg'])
                self.app.setEntryFg(
                    "Puerto de datos",
                    self.colors['entry_fg'])
                for button in ["Registrarme", "Cerrar"]:
                    self.app.setButtonBg(button, self.colors['button_bg'])
                    pass

        # Preparación del interfaz
        self.app.addLabel("title", "Cliente Multimedia P2P - Redes2 ")
        try:
            self.app.addImage("video", "imgs/webcam.gif")
        except Exception:
            print("imgs/webcam.gif not found.\n"
                  "A gif inside the folder imgs is required "
                  "to run the application. Exiting")
            exit(1)

        # Registramos la función de captura de video
        # Esta misma función también sirve para enviar un vídeo
        self.capName = "imgs/webcam.gif"
        self.cap = cv2.VideoCapture(self.capName)
        self.recvFps = 30
        self.completeSelection(False)
        self.heightSmall = self.maxWidthSmall
        self.inputDevice = "GIF"  # To show on the GUI

        self.cap2 = cv2.VideoCapture(self.capName)
        self.app.setPollTime(50)
        self.app.registerEvent(self.muestraVideo)
        self.app.registerEvent(self.muestraInfo)

        # Añadir los botones
        self.app.addButtons(["Llamar", "Colgar",
                            "Play/Pause", "Salir"], self.buttonsCallback)
        for button in ["Llamar", "Colgar", "Play/Pause", "Salir"]:
            self.app.setButtonBg(button, self.colors['button_bg'])
            pass

        self.myNick = ""
        self.otherNick = ""
        self.myPortTcp = 0
        self.myPortUdp = 0
        self.otherPortTcp = 0
        self.otherPortUdp = 0
        self.myIP = ""
        self.otherIP = ""

        # Barra de estado
        # Debe actualizarse con información útil sobre la llamada (duración,
        # FPS, etc...)
        self.app.addStatusbar(fields=4)

        self.app.createMenu("Dispositivo de entrada")
        # self.app.addMenuList(
        #     "Dispositivo de entrada", ["Selecciona uno", "-"], None)
        # self.app.disableMenuItem("Dispositivo de entrada", "Selecciona uno")
        self.app.addMenuRadioButton(
            "Dispositivo de entrada",
            "Input",
            "GIF",
            self.selectGIF)
        self.app.addMenuRadioButton(
            "Dispositivo de entrada",
            "Input",
            "Vídeo",
            self.selectVideo)
        self.app.addMenuRadioButton(
            "Dispositivo de entrada",
            "Input",
            "Cámara",
            self.selectCamera)
        self.app.addMenuRadioButton(
            "Dispositivo de entrada",
            "Input",
            "Compartir Pantalla",
            self.selectScreen)

        # Show the chosen one
        self.app.setMenuRadioButton(
            "Dispositivo de entrada",
            "Input",
            self.inputDevice)

        self.app.createMenu("Calidad de capturadora")
        self.app.addMenuRadioButton(
            "Calidad de capturadora",
            "Input2",
            "Baja",
            self.cambiaResolucion)
        self.app.addMenuRadioButton(
            "Calidad de capturadora",
            "Input2",
            "Media",
            self.cambiaResolucion)
        self.app.addMenuRadioButton(
            "Calidad de capturadora",
            "Input2",
            "Alta",
            self.cambiaResolucion)
        # Show the chosen one
        self.app.setMenuRadioButton("Calidad de capturadora", "Input2", "Alta")
        self.qualityScaler = 1.0

        self.app.createMenu("Porcentaje de compresión")
        self.app.addMenuRadioButton(
            "Porcentaje de compresión",
            "Input3",
            "0%",
            self.cambiaCalidad)
        self.app.addMenuRadioButton(
            "Porcentaje de compresión",
            "Input3",
            "25%",
            self.cambiaCalidad)
        self.app.addMenuRadioButton(
            "Porcentaje de compresión",
            "Input3",
            "50%",
            self.cambiaCalidad)
        self.app.addMenuRadioButton(
            "Porcentaje de compresión",
            "Input3",
            "75%",
            self.cambiaCalidad)
        self.app.addMenuRadioButton(
            "Porcentaje de compresión",
            "Input3",
            "100%",
            self.cambiaCalidad)
        # Show the chosen one
        self.app.setMenuRadioButton(
            "Porcentaje de compresión", "Input3", "50%")
        self.encodingQuality = 50

        # Atributos para mostrar en la llamada
        self.call_start_time = time.time()
        self.playing = False
        self.numeroOrden = 0
        self.inACall = False

        self.videoBuff = {"big": None, "small": None}

        self.threadRecv = Thread(target=self.recibeVideo)
        self.threadSend = Thread(target=self.capturaVideo)
        self.threadCall = Thread(target=self.callListener)
        self.threadKill = False
        self.myProtos = ["V0", "V1"]
        self.versionInUse = 0

    def cambiaResolucion(self):
        calidad = self.app.getMenuRadioButton(
            "Calidad de capturadora", "Input2")
        if calidad == "Baja":
            self.qualityScaler = 0.5
        elif calidad == "Media":
            self.qualityScaler = 0.75
        elif calidad == "Alta":
            self.qualityScaler = 1.0

    def cambiaCalidad(self):
        calidad = self.app.getMenuRadioButton(
            "Porcentaje de compresión", "Input3")
        # 0% de compresion es 100% de calidad
        if calidad == "0%":
            self.encodingQuality = 100
        elif calidad == "25%":
            self.encodingQuality = 75
        elif calidad == "50%":
            self.encodingQuality = 50
        elif calidad == "75%":
            self.encodingQuality = 25
        elif calidad == "100%":
            self.encodingQuality = 0

    def checkStop(self):
        ret = self.app.yesNoBox(
            "Confirma salida",
            "¿Estás seguro de que quieres salir?")
        if ret:
            self.threadKill = True
            self.sendBufClass.stop()
            self.recvBufClass.stop()
            try:
                callEnd(self.myNick, self.otherIP, self.otherPortTcp)
            except Exception:
                pass
        return ret

    def completeSelection(self, screenShare):
        self.doScreenShare = screenShare
        if screenShare:
            self.sendFps = 60
        else:
            self.sendFps = self.cap.get(cv2.CAP_PROP_FPS)
        self.theoreticalSendFps = self.sendFps

    def selectGIF(self):
        self.capName = "imgs/webcam.gif"
        self.cap = cv2.VideoCapture(self.capName)
        self.inputDevice = "GIF"
        self.completeSelection(False)

    def selectVideo(self):
        video_path = self.app.openBox(
            title="Selección de vídeo",
            dirName=".",
            fileTypes=SUPPORTED_VIDEO_FILES
        )

        if not video_path:
            # Keep the previous input device
            self.app.setMenuRadioButton(
                "Dispositivo de entrada",
                "Input",
                self.inputDevice)
            return

        try:
            self.cap = cv2.VideoCapture(video_path)
        except Exception:
            # Keep the previous input device
            self.app.setMenuRadioButton(
                "Dispositivo de entrada",
                "Input",
                self.inputDevice)
        else:
            self.inputDevice = "Vídeo"
            self.capName = video_path
            self.completeSelection(False)

    def selectCamera(self):
        try:
            cap = cv2.VideoCapture(0)
            self.cap = cap
            self.capName = 0
            self.inputDevice = "Cámara"
            self.completeSelection(False)
        except Exception:
            pass

    def selectScreen(self):
        self.inputDevice = "Compartir Pantalla"
        self.completeSelection(True)

    def start(self):
        self.app.showSubWindow("Registro")
        try:
            self.app.go()
        except Exception:
            pass

    # Función que captura el frame a mostrar en cada momento
    def capturaVideo(self):
        # print("1 capturaVideo")
        startTime = time.time()
        realFps = self.sendFps

        prevData = None
        while not self.threadKill:
            processingTime = time.time() - startTime
            timeToSleep = 1 / self.theoreticalSendFps - processingTime

            if timeToSleep < 0:
                realFps = 1 / processingTime
                self.sendFps = realFps
                timeToSleep = 0
            elif self.sendFps < self.theoreticalSendFps and timeToSleep > 0.001:
                # Permitir que se suban los fps si hay capacidad
                self.sendFps *= (1 + timeToSleep /
                                 (timeToSleep + processingTime))
                if self.sendFps > self.theoreticalSendFps:
                    self.sendFps = self.theoreticalSendFps
                timeToSleep = 0
            else:
                realFps = self.sendFps

            time.sleep(timeToSleep)
            startTime = time.time()

            # Capturamos un frame de la cámara o del vídeo
            if not self.doScreenShare:
                ret, frame = self.cap.read()
                if not ret:
                    self.cap.open(self.capName)
                    ret, frame = self.cap.read()
                    if not ret:
                        continue
                    self.sendFps = self.cap.get(cv2.CAP_PROP_FPS)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                maxWidthSmall = self.maxWidthBig
                printscreen_pil = self.screenCapture.grab()
                if printscreen_pil is None:
                    return
                maxHeightSmall = int(
                    maxWidthSmall /
                    printscreen_pil.size[1] *
                    printscreen_pil.size[0])
                printscreen_pil = printscreen_pil.resize(
                    (maxHeightSmall, maxWidthSmall))
                printscreen_numpy = np.array(printscreen_pil)
                frame = printscreen_numpy

            h = frame.shape[0]  # scale h
            w = frame.shape[1]  # scale w
            self.heightSmall = int(h * self.maxWidthSmall / w)
            heightBig = int(
                self.maxWidthBig /
                self.maxWidthSmall *
                self.heightSmall)
            frame = cv2.resize(frame,
                               (int(self.maxWidthBig * self.qualityScaler),
                                int(heightBig * self.qualityScaler)))

            encode_param = [cv2.IMWRITE_JPEG_QUALITY, self.encodingQuality]
            ret, encimg = cv2.imencode('.jpg', frame, encode_param)

            # Invertir la imagen horizontalmente para ver bien la webcam
            frameToShow = frame
            if self.inputDevice == "Cámara":
                frameToShow = cv2.flip(frame, 1)

            # Lo ponemos para mostrar en la GUI
            self.videoBuff["small"] = frameToShow

            if not self.playing:
                continue

            encimg = encimg.tobytes()
            data = self.packData(encimg)

            if self.versionInUse == 1:
                data2 = prevData
                data = self.packDataV1(data, data2)

                frame = cv2.resize(frame,
                                   (int(self.maxWidthBig * self.qualityScaler / 3),
                                    int(heightBig * self.qualityScaler / 3)))
                encode_param = [cv2.IMWRITE_JPEG_QUALITY, self.encodingQuality]
                ret, encimg = cv2.imencode('.jpg', frame, encode_param)
                encimg = encimg.tobytes()
                prevData = self.packData(encimg)

            try:
                self.sendBuf.write(data)
            except Exception:
                continue

            self.numeroOrden += 1
        # print("0 capturaVideo")

    def recibeVideo(self):
        # print("1 recibeVideo")
        shouldWait = True

        timeWithoutFrame = 0.0
        while not self.threadKill:
            time.sleep(1 / self.recvFps)

            # Si el video ha sido pausado, deberemos de
            # vaciar el buffer de recepcion
            if not self.playing and self.inACall:
                self.recvBuf.clear()
                shouldWait = True
                continue

            # Not waiting for buffering
            if timeWithoutFrame > 10 and self.inACall:
                # No frames received. Consider the call dead
                self.cuelgaLlamada()
                timeWithoutFrame = 0.0
                self.app.errorBox(
                    "Error en la llamada", "Usuario ausente. "
                    "No se han recibido datos durante los últimos 10 segundos.\n"
                    "Cortando comunicación.")
            while not self.threadKill and shouldWait:
                time.sleep(1 / self.recvFps)
                # Esperamos a que el buffer este lleno
                if self.inACall and not self.playing:
                    # Waiting for buffering
                    if timeWithoutFrame > 10:
                        # No frames received. Consider the call dead
                        self.cuelgaLlamada()
                        timeWithoutFrame = 0.0
                        self.app.errorBox(
                            "Error en la llamada", "Usuario ausente. "
                            "No se han recibido suficientes datos durante los últimos 10 segundos.\n"
                            "Cortando comunicación.")
                        break
                    else:
                        timeWithoutFrame += 1 / self.recvFps

                if self.recvBuf.isFull():
                    shouldWait = False
                    break
            try:
                data = self.recvBuf.read()
                timeWithoutFrame = 0.0
            except Exception:
                if self.inACall:
                    timeWithoutFrame += 1 / self.recvFps
                continue

            # width and height podrian no ser usados,
            # ya que el frame ya contiene estos parámetros
            # pero al cambiar la resolucion del paquete 
            # provoca un glitch de cambio de resolucion 
            # algo molesto
            try:
                # num order and timestamp are not used
                # as they are not necessary at this point
                n, ts, w, h, fps, encimg = self.unpackData(data)
            except Exception:
                continue
            frame = cv2.imdecode(np.frombuffer(encimg, np.uint8), 1)
            self.recvFps = fps

            # Conversión de formato para su uso en el GUI
            # Escalamos la imagen apropiadamente
            self.heightBig = int(self.maxWidthBig * h / w)
            frame = cv2.resize(frame, (self.maxWidthBig, self.heightBig))

            self.videoBuff["big"] = frame
        # print("0 recibeVideo")

    def packDataV1(self, data1, data2):
        """ Prepares data to send with version 1 implementation """
        data = (str(len(data1)) + " ").encode()
        data += data1
        if not data2:
            data2 = b''
        data += (" " + str(len(data2)) + " ").encode()
        data += data2
        return data

    def packData(self, encimg):
        """ Returns packed data """
        fps = self.sendFps
        scale = self.maxWidthBig / self.maxWidthSmall
        width = int(self.maxWidthSmall * scale)
        height = int(self.heightSmall * scale)
        data = str(self.numeroOrden) + "#"
        data += str(time.time()) + "#"
        data += str(width) + "x" + str(height) + "#"
        data += str(fps) + "#"
        data = data.encode()
        data += encimg
        return data

    def unpackData(self, data):
        """ Returns a 6-tuple """
        dataList = data.split(b'#', 4)
        try:
            numOrd = int(dataList[0])
            timestamp = float(dataList[1])
            width, height = dataList[2].split(b'x')
            width = int(width)
            height = int(height)
            fps = float(dataList[3])
            encimg = dataList[4]
        except Exception:
            raise Exception("Corrupt packet")
        return (numOrd, timestamp, width, height, fps, encimg)

    def muestraVideo(self):
        if self.inACall:
            compose = True
            fr_peque = self.videoBuff["small"]
            fr_comp = self.videoBuff["big"]
            if fr_peque is None:
                return
            if fr_comp is None:
                fr_comp = fr_peque
                heightBig = int(
                    self.maxWidthBig /
                    self.maxWidthSmall *
                    self.heightSmall)
                fr_comp = cv2.resize(fr_comp, (self.maxWidthBig, heightBig))
                compose = False
            if fr_peque is not None and fr_comp is not None:
                fr_peque = cv2.resize(
                    fr_peque, (self.maxWidthSmall, self.heightSmall))
                if compose:
                    fr_comp[0:fr_peque.shape[0],
                            0:fr_peque.shape[1]] = fr_peque

                img_tk = ImageTk.PhotoImage(Image.fromarray(fr_comp))
                self.app.setImageData("video", img_tk, fmt='PhotoImage')
                self.app.setImageSize("video", img_tk.width(), img_tk.height())
        else:
            fr_comp = self.videoBuff["small"]
            if fr_comp is not None:
                heightBig = int(
                    self.maxWidthBig /
                    self.maxWidthSmall *
                    self.heightSmall)
                fr_comp = cv2.resize(fr_comp, (self.maxWidthBig, heightBig))
                img_tk = ImageTk.PhotoImage(Image.fromarray(fr_comp))
                self.app.setImageData("video", img_tk, fmt='PhotoImage')
                self.app.setImageSize("video", img_tk.width(), img_tk.height())

    # Función que gestiona los callbacks de los botones

    def buttonsCallback(self, button):
        if button == "Salir":
            # Salimos de la aplicación
            self.app.stop()

        elif button == "Llamar":
            # Entrada del nick del usuario a conectar
            nick = self.app.textBox(
                "Conexión", "Introduce el nick del usuario a buscar")
            if not nick:
                return
            try:
                ret = listUsers()
            except Exception as e:
                print(e)
                self.app.errorBox(
                    "Error listando usuarios",
                    "No se pudo establecer una conexión al servidor de búsqueda")
                return
            users = [user for user in ret if nick.lower()
                     in user[dsKeys.nick].lower()]
            with self.app.subWindow("Lista de usuarios", modal=True):
                self.app.setBg(self.colors['bg'], override=True)
                self.app.setFg(self.colors['fg'], override=True)
                self.app.emptyCurrentContainer()
                self.app.setSticky("ew")
                self.app.setPadding([5, 5])
                if users:
                    with self.app.scrollPane("User scroll"):
                        for user in users:
                            self.app.addRadioButton(
                                "user",
                                str(user[dsKeys.nick]) + " (" +
                                str(user[dsKeys.ip]) + ":" +
                                str(user[dsKeys.port]) + ")")

                self.app.addButtons(["Aceptar", "Atras"],
                                    self.seleccionUsuario, 4, 0, 2)
            self.app.showSubWindow("Lista de usuarios")

        elif button == "Colgar":
            self.cuelgaLlamada()
        elif button == "Play/Pause":
            if self.otherNick:
                try:
                    if self.playing:
                        callHold(self.myNick, self.otherIP, self.otherPortTcp)
                    else:
                        callResume(
                            self.myNick, self.otherIP, self.otherPortTcp)
                    self.playing = not self.playing
                except Exception:
                    pass

    def cuelgaLlamada(self):
        self.playing = False
        self.inACall = False
        self.sendBufClass.stop()
        try:
            otherIP = self.otherIP
            otherPortTcp = self.otherPortTcp
            self.otherIP = ""
            self.otherNick = ""
            self.otherPortTcp = 0
            self.otherPortUdp = 0
            self.videoBuff["big"] = None
            self.app.clearStatusbar(field=2)
            callEnd(self.myNick, otherIP, otherPortTcp)
        except Exception:
            pass
        self.recvBufClass.clear()

    def seleccionUsuario(self, button):
        if button == "Aceptar":
            text = self.app.getRadioButton("user")
            user = text.split("(", 1)[0][:-1]
            try:
                protos = query(user)[dsKeys.protocol]
            except Exception:
                self.app.errorBox(
                    "Error en búsqueda",
                    "Usuario no encontrado en el servidor",
                    parent="Lista de usuarios")
                return

            sharedProtos = [
                proto for proto in protos if proto.upper() in self.myProtos]

            if len(sharedProtos) == 0:
                self.app.errorBox(
                    "No hay protocolos en común",
                    "El usuario seleccionado no tiene ningún "
                    "protocolo en común con esta aplicación",
                    parent="Lista de usuarios")
            elif len(sharedProtos) == 1:
                ipport = text.split("(")[1][:-1]

                self.llamando(ipport, sharedProtos[0])

            else:
                with self.app.subWindow("Lista de protocolos", modal=True):
                    self.app.setBg(self.colors['bg'], override=True)
                    self.app.setFg(self.colors['fg'], override=True)
                    self.app.emptyCurrentContainer()
                    self.app.setSticky("ew")
                    self.app.setPadding([5, 5])
                    if protos:
                        with self.app.scrollPane("User scroll 2"):
                            for proto in sharedProtos:
                                self.app.addRadioButton("proto", proto)

                    self.app.addButtons(["Confirmar", "Atrás"],
                                        self.seleccionProtocolo, 4, 0, 2)
                self.app.showSubWindow("Lista de protocolos")

        elif button == "Atras":
            self.app.emptySubWindow("Lista de usuarios")

        self.app.hideSubWindow("Lista de usuarios")

    def seleccionProtocolo(self, button):
        if button == "Confirmar":
            text = self.app.getRadioButton("user")
            ipport = text.split("(")[1][:-1]
            proto = self.app.getRadioButton("proto")
            self.llamando(ipport, proto)
        elif button == "Atrás":
            self.app.emptySubWindow("Lista de protocolos")
        self.app.hideSubWindow("Lista de protocolos")

    def llamando(self, ipport, proto="V0"):
        ip, port = None, None
        while True:
            ip, port = ipport.split(":")

            from socket import inet_aton
            try:
                inet_aton(ip)
            except Exception:
                pass
            if port.isnumeric():  # both ip and port are valid
                port = int(port)
                break

        kwargs = {'ip': ip, 'port': port, 'proto': proto}
        hilo = Thread(target=self.pruebaLlamar, kwargs=kwargs)
        hilo.daemon = True
        hilo.start()

    def protoVersion(self, proto):
        if proto == "V0":
            return 0
        return 1

    def pruebaLlamar(self, ip, port, proto):
        # print("1 pruebaLlamar")
        try:
            # Si estabamos en llamada, la colgamos primero y procedemos a
            # llamar
            self.cuelgaLlamada()
            ret = calling(self.myNick, self.myPortUdp, ip, port, proto)
            otherIP = ip
            otherPortUdp = ret[controlKeys.port]
            v = self.protoVersion(proto)
            self.recvBufClass.setVersion(v)
            self.sendBufClass.start(otherIP, otherPortUdp, v)
        except Exception as e:
            self.app.errorBox(
                "Error llamando",
                "No se pudo establecer una conexión a " +
                ip + ":" + str(port) + "\nError: " + str(e)
            )
        else:
            self.versionInUse = v
            self.otherIP = otherIP
            self.otherPortUdp = otherPortUdp
            self.otherPortTcp = port
            self.otherNick = ret[controlKeys.nick]
            self.playing = True
            self.inACall = True
            self.call_start_time = time.time()
            self.app.setStatusbar(
                "Hablando con " +
                self.otherNick +
                " at " +
                otherIP +
                ":" +
                str(otherPortUdp),
                2)
        # print("0 pruebaLlamar")

    def registroCallback(self, button):

        if button == "Cerrar":
            self.app.stop()
        elif button == "Registrarme":
            myNick = str(self.app.getEntry("Nickname"))
            if myNick == "":
                self.app.errorBox("Nick inválido",
                                  "Por favor, introduzca un nickname válido")
                return
            myPasswd = str(self.app.getEntry("Contraseña"))
            if myPasswd == "":
                self.app.errorBox(
                    "Contraseña inválida",
                    "Por favor, introduzca una contraseña válida")
                return
            myIP = str(self.app.getEntry("IP"))
            try:
                inet_aton(myIP)
            except Exception:
                self.app.errorBox(
                    "IP inválida",
                    "Por favor, introduzca una IP válida")
                return
            myPortTcp = str(self.app.getEntry("Puerto de control"))
            if not myPortTcp.isnumeric() or int(
                    myPortTcp) <= 2**10 or int(myPortTcp) >= 2**16:
                self.app.errorBox(
                    "Puerto inválido",
                    "Por favor, introduzca un puerto válido")
                return
            myPortTcp = int(myPortTcp)
            myPortUdp = str(self.app.getEntry("Puerto de datos"))
            if not myPortUdp.isnumeric() or int(
                    myPortUdp) <= 2**10 or int(myPortTcp) >= 2**16:
                self.app.errorBox(
                    "Puerto inválido",
                    "Por favor, introduzca un puerto válido")
                return
            myPortUdp = int(myPortUdp)

            try:
                register(myNick, myPasswd, myIP, myPortTcp, self.myProtos)
            except Exception as e:
                self.app.errorBox(
                    "Error registrando",
                    "Hubo un error en el registro. "
                    "Por favor, inténtelo de nuevo más tarde\n"
                    "Error: " + str(e))
                return

            try:
                self.recvBufClass.start(myIP, myPortUdp)
            except Exception:
                self.app.errorBox(
                    "Error abriendo socket",
                    "Hubo un error abriendo el socket de recepción. "
                    "Por favor, inténtelo de nuevo más tarde\n")
                return
            self.myIP = myIP
            self.myNick = myNick
            self.myPortTcp = myPortTcp
            self.myPortUdp = myPortUdp
            self.threadRecv.start()
            self.threadSend.start()
            self.threadCall.start()
            self.app.setStatusbar(self.myNick + " at " +
                                  self.myIP + ":" + str(self.myPortUdp), 1)
            self.app.hideSubWindow("Registro")

    def muestraInfo(self):
        if self.playing:
            # Calcular FPS
            current_time = time.time()

            fps = self.sendFps

            fps_str = 'FPS: {0:.2f}'.format(fps)

            duration = current_time - self.call_start_time
            call_time = datetime.datetime.utcfromtimestamp(duration)
            time_str = 'Duración: ' + call_time.strftime('%H:%M:%S')

            self.app.setStatusbar(fps_str, 0)
            self.app.setStatusbar(time_str, 3)
        else:
            self.app.setStatusbar("FPS: -", 0)
            self.app.setStatusbar("Duración: -", 3)

    def callListener(self):
        # print("1 callListener")
        listenSocket = TCPUtil.createServer(self.myIP, self.myPortTcp)
        while not self.threadKill:
            try:
                cliSock = TCPUtil.acceptConnection(listenSocket, 1)
            except Exception:
                continue
            data = TCPUtil.recvInfo(cliSock)
            if not data:
                TCPUtil.closeConnection(cliSock)
                continue
            arguments = data.split(" ")
            if len(arguments) < 1:
                TCPUtil.closeConnection(cliSock)
                continue
            if arguments[0] == "CALLING":
                if len(arguments) < 3:  # llamada maliciosa
                    TCPUtil.closeConnection(cliSock)
                    continue
                if not arguments[2].isnumeric():  # llamada maliciosa
                    TCPUtil.closeConnection(cliSock)
                    continue
                proto = "V0"
                if len(arguments) >= 4:
                    proto = arguments[3]
                if proto.upper() not in self.myProtos:
                    callDeny(cliSock, self.myNick)
                    TCPUtil.closeConnection(cliSock)
                    continue
                if self.inACall:
                    print("Estoy busy")
                    callBusy(cliSock)
                else:
                    ret = self.app.yesNoBox(
                        arguments[1] + " te está llamando",
                        "Estas recibiendo una llamada de " +
                        arguments[1] + ", con protocolo " + proto +
                        ".\n¿Quieres aceptarla?")
                    if ret:
                        try:
                            q = query(arguments[1])
                            otherNick = q[dsKeys.nick]
                            otherPortUdp = int(arguments[2])
                            otherPortTcp = q[dsKeys.port]
                            otherIP = q[dsKeys.ip]
                            v = self.protoVersion(proto)
                            if self.myNick != otherNick:
                                self.recvBufClass.setVersion(v)
                                self.sendBufClass.start(
                                    otherIP, otherPortUdp, v)
                            self.recvBufClass.clear()
                            callAccept(cliSock, self.myNick, self.myPortUdp)
                        except Exception:
                            self.app.errorBox(
                                "Error de comunicación",
                                "No se ha encontrado el usuario llamante "
                                "en el servidor de búsqueda")
                        else:
                            self.versionInUse = v
                            self.otherNick = otherNick
                            self.otherPortTcp = otherPortTcp
                            self.otherPortUdp = otherPortUdp
                            self.otherIP = otherIP
                            self.inACall = True
                            self.playing = True
                            self.call_start_time = time.time()
                            self.app.setStatusbar(
                                "Hablando con " + otherNick + " at " +
                                otherIP + ":" + str(otherPortUdp),
                                2)

                    else:
                        callDeny(cliSock, self.myNick)
            else:
                if len(arguments) != 2:
                    TCPUtil.closeConnection(cliSock)
                    continue
                if arguments[0] == "CALL_HOLD":
                    # Checking if the call holder is the appropriate person
                    if arguments[1] == self.otherNick and self.myNick != self.otherNick:
                        self.playing = False
                elif arguments[0] == "CALL_RESUME":
                    if arguments[1] == self.otherNick and self.myNick != self.otherNick:
                        self.playing = True
                elif arguments[0] == "CALL_END":
                    if arguments[1] == self.otherNick and self.myNick != self.otherNick:
                        self.playing = False
                        self.inACall = False
                        self.otherIP = ""
                        self.otherNick = ""
                        self.otherPortUdp = 0
                        self.otherPortTcp = 0
                        self.videoBuff["big"] = None
                        self.app.clearStatusbar(field=2)
                        self.sendBufClass.stop()

            TCPUtil.closeConnection(cliSock)
        TCPUtil.closeConnection(listenSocket)
        # print("0 callListener")
