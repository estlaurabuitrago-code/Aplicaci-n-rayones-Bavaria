from kivy.config import Config
Config.set('graphics', 'width', '360')
Config.set('graphics', 'height', '640')

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager
from pantallas.login import LoginScreen
from pantallas.register import RegisterScreen
from pantallas.home import HomeScreen


class Gestorpantallas(ScreenManager):
    pass

class MiApp(App):
    def build(self):
        # NO necesitamos unload_file a menos que estemos reiniciando la app en vivo
        
        # Cargamos los archivos KV directamente
        try:
            Builder.load_file('kv/login.kv')   
            Builder.load_file('kv/register.kv')
            Builder.load_file('kv/home.kv')
        except Exception as e:
            print(f"Error cargando archivos KV: {e}")

        sm = ScreenManager()
        # Importante: Asegúrate de que las clases LoginScreen, etc., 
        # coincidan con lo que definiste en los archivos .py
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(RegisterScreen(name='register'))
        sm.add_widget(HomeScreen(name='home'))
        
        return sm
if __name__ == "__main__":
    MiApp().run()
    #Aplicacion = MiApp()
    #Aplicacion.run()