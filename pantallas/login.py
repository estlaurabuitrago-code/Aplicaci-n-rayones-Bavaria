from kivy.uix.screenmanager import Screen

class LoginScreen(Screen):
    # Usaremos 'ir_a_inicio' para que no haya duda de que es nueva
    def ir_a_inicio(self):
        print("Botón presionado: Cambiando a Home")
        # El manager es el ScreenManager que creamos en el main
        if self.manager:
            self.manager.current = 'home'