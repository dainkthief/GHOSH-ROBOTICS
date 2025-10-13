from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.core.window import Window
import os

class NotepadLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        Window.size = (600, 400)
        self.add_widget(Label(text="GHOSH ROBOTICS", size_hint_y=None, height=40))
        self.text = TextInput(multiline=True, font_size=16)
        self.add_widget(self.text)

        btns = BoxLayout(size_hint_y=None, height=50)
        save_btn = Button(text="Save As")
        save_btn.bind(on_release=self.save_as)
        clear_btn = Button(text="Clear")
        clear_btn.bind(on_release=lambda x: setattr(self.text, "text", ""))
        btns.add_widget(save_btn)
        btns.add_widget(clear_btn)
        self.add_widget(btns)

    def save_as(self, instance):
        chooser = FileChooserListView(path=os.getcwd(), filters=["*.txt"])
        popup = Popup(title="Select save location", content=chooser, size_hint=(0.9, 0.9))

        def save_selected(obj, selection):
            if selection:
                with open(selection[0], "w", encoding="utf-8") as f:
                    f.write(self.text.text)
                popup.dismiss()

        chooser.bind(on_submit=save_selected)
        popup.open()

class GHOSHRoboticsApp(App):
    def build(self):
        self.title = "GHOSH ROBOTICS"
        return NotepadLayout()

if __name__ == "__main__":
    GHOSHRoboticsApp().run()
