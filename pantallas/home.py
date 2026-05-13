import os
import numpy as np
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.utils import platform
from kivy.factory import Factory

class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.contador_frames = 0
        self.frecuencia_deteccion = 10
        self.ultimos_cuadros = []
        self.model = None
        self.interpreter = None
        self.input_details = None
        self.output_details = None
        self.capture = None
        self.camara_activa = False
        Clock.schedule_once(self.solicitar_permisos_y_cargar, 0.5)

    def solicitar_permisos_y_cargar(self, dt):
        if platform == 'android':
            try:
                from android.permissions import request_permissions, Permission  # type: ignore
                request_permissions(
                    [Permission.CAMERA,
                     Permission.READ_EXTERNAL_STORAGE,
                     Permission.WRITE_EXTERNAL_STORAGE],
                    self._callback_permisos
                )
            except Exception as e:
                print(f"Error permisos: {e}")
                self.cargar_modelo_ia(0)
        else:
            self.cargar_modelo_ia(0)

    def _callback_permisos(self, permissions, grants):
        self.cargar_modelo_ia(0)

    def cargar_modelo_ia(self, dt):
        try:
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            if platform == 'android':
                rutas = [
                    os.path.join(BASE_DIR, 'modelos', 'buenito1.tflite'),
                    os.path.join(BASE_DIR, '..', 'modelos', 'buenito1.tflite'),
                ]
                ruta = next((r for r in rutas if os.path.exists(r)), None)
                if ruta:
                    self._cargar_tflite(ruta)
                else:
                    print("Modelo no encontrado")
            else:
                ruta = os.path.join(BASE_DIR, '..', 'modelos', 'buenito1.tflite')
                self._cargar_ultralytics(ruta)
        except Exception as e:
            print(f"Error cargar modelo: {e}")

    def _cargar_ultralytics(self, ruta):
        try:
            from ultralytics import YOLO
            self.model = YOLO(ruta, task='segment')
            print("Ultralytics cargado OK")
        except Exception as e:
            print(f"Error YOLO: {e}")

    def _cargar_tflite(self, ruta):
        try:
            import tflite_runtime.interpreter as tflite  # type: ignore
            self.interpreter = tflite.Interpreter(model_path=ruta)
            self.interpreter.allocate_tensors()
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            print("TFLite cargado OK")
        except Exception as e:
            print(f"Error TFLite: {e}")

    def on_leave(self, *args):
        self.detener_camara()

    # ── CONTROL CAMARA ───────────────────────
    def toggle_camara(self):
        if not self.camara_activa:
            self.iniciar_camara()
            self.ids.btn_camara.text = "DETENER"
            self.ids.btn_camara.background_color = (0.8, 0, 0, 1)
        else:
            self.detener_camara()
            self.ids.btn_camara.text = "INICIAR DETECCION"
            self.ids.btn_camara.background_color = (0.4, 0.2, 0.6, 1)

    def iniciar_camara(self):
        try:
            if platform == 'android':
                # Activar widget Camera de Kivy
                if 'live_image' in self.ids and hasattr(self.ids.live_image, 'play'):
                    self.ids.live_image.play = True
            else:
                import cv2
                self.capture = cv2.VideoCapture(0)
            self.camara_activa = True
            Clock.schedule_interval(self.actualizar_frame, 1.0 / 30.0)
        except Exception as e:
            print(f"Error iniciando camara: {e}")

    def detener_camara(self):
        try:
            self.camara_activa = False
            Clock.unschedule(self.actualizar_frame)
            if self.capture:
                self.capture.release()
                self.capture = None
            if platform == 'android' and 'live_image' in self.ids:
                if hasattr(self.ids.live_image, 'play'):
                    self.ids.live_image.play = False
        except Exception as e:
            print(f"Error deteniendo camara: {e}")

    # ── FRAMES ───────────────────────────────
    def actualizar_frame(self, dt):
        try:
            if platform == 'android':
                self._frame_android()
            else:
                self._frame_pc()
        except Exception as e:
            print(f"Error frame: {e}")

    def _frame_pc(self):
        import cv2
        if not self.capture:
            return
        ret, frame = self.capture.read()
        if not ret:
            return

        self.contador_frames += 1
        if self.contador_frames >= self.frecuencia_deteccion and self.model:
            results = self.model(frame, conf=0.25, verbose=False)
            self.ultimos_cuadros = []
            for r in results:
                if r.boxes:
                    self.ultimos_cuadros = r.boxes.data.cpu().numpy()
            self.contador_frames = 0

        for box in self.ultimos_cuadros:
            x1, y1, x2, y2 = box[:4]
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)

        # PC usa cv2 para flip
        buf = cv2.flip(frame, 0).tobytes()
        texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
        texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.ids.live_image.texture = texture

    def _frame_android(self):
        # En Android capturamos desde el widget Camera de Kivy
        if 'live_image' not in self.ids:
            return
        camara = self.ids.live_image
        if not hasattr(camara, 'texture') or not camara.texture:
            return

        tex = camara.texture
        buf = tex.pixels
        frame = np.frombuffer(buf, dtype=np.uint8).copy()
        frame = frame.reshape(tex.height, tex.width, 4)
        frame = frame[:, :, :3]  # RGBA -> RGB

        self.contador_frames += 1
        if self.contador_frames >= self.frecuencia_deteccion and self.interpreter:
            self._inferir_tflite(frame)
            self.contador_frames = 0

        # Dibujar cajas SIN cv2
        for box in self.ultimos_cuadros:
            try:
                x1 = max(0, int(box[0]))
                y1 = max(0, int(box[1]))
                x2 = min(frame.shape[1]-1, int(box[2]))
                y2 = min(frame.shape[0]-1, int(box[3]))
                frame[y1:y1+3, x1:x2] = [255, 0, 0]
                frame[y2:y2+3, x1:x2] = [255, 0, 0]
                frame[y1:y2, x1:x1+3] = [255, 0, 0]
                frame[y1:y2, x2:x2+3] = [255, 0, 0]
            except:
                pass

        # Android SIN cv2 — flip con numpy
        buf = np.flipud(frame).tobytes()
        texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='rgb')
        texture.blit_buffer(buf, colorfmt='rgb', bufferfmt='ubyte')
        self.ids.live_image.texture = texture

    def _inferir_tflite(self, frame):
        try:
            from PIL import Image
            img = Image.fromarray(frame).resize((640, 640))
            inp = np.expand_dims(np.array(img, dtype=np.float32) / 255.0, axis=0)
            self.interpreter.set_tensor(self.input_details[0]['index'], inp)
            self.interpreter.invoke()
            output = self.interpreter.get_tensor(self.output_details[0]['index'])
            self.ultimos_cuadros = output[0] if len(output) > 0 else []
        except Exception as e:
            print(f"Error inferencia: {e}")
            self.ultimos_cuadros = []

    def abrir_menu(self):
        try:
            Factory.MenuDesplegable().open()
        except Exception as e:
            print(f"Error menu: {e}")

    def cerrar_sesion(self):
        self.detener_camara()
        self.manager.current = 'login'