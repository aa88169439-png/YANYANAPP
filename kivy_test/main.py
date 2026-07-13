from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
import threading

from api.translator import translate, CATEGORY_MAP
from database.offline_database import init_offline_db
from config.config import load_config


class YinYinTestApp(App):
    def build(self):
        init_offline_db()
        self.title = "YinYin"
        
        root = BoxLayout(orientation="vertical", padding=10, spacing=6)
        
        self.label = Label(text="YinYin - Chinese Learning", size_hint_y=None, height=40, bold=True)
        root.add_widget(self.label)
        
        self.input = TextInput(hint_text="Type English here...", multiline=False, size_hint_y=None, height=50)
        root.add_widget(self.input)
        
        btn = Button(text="Translate", size_hint_y=None, height=50)
        btn.bind(on_press=self.do_translate)
        root.add_widget(btn)
        
        self.scroll = ScrollView()
        self.output = GridLayout(cols=1, spacing=4, size_hint_y=None)
        self.output.bind(minimum_height=self.output.setter("height"))
        self.scroll.add_widget(self.output)
        root.add_widget(self.scroll)
        
        self.status = Label(text="Ready", size_hint_y=None, height=30)
        root.add_widget(self.status)
        
        return root
    
    def do_translate(self, btn):
        text = self.input.text.strip()
        if not text:
            return
        self.status.text = "Translating..."
        threading.Thread(target=self._translate, args=(text,), daemon=True).start()
    
    def _translate(self, text):
        try:
            result = translate(text, "daily")
            Clock.schedule_once(lambda dt: self.show_result(result))
        except Exception as e:
            Clock.schedule_once(lambda dt: self.show_error(str(e)))
    
    def show_result(self, result):
        self.output.clear_widgets()
        for key in ["natural_chinese", "literal_translation", "pinyin", "culture_note"]:
            val = result.get(key, "")
            if val:
                self.output.add_widget(Label(text=f"{key}: {val}", size_hint_y=None, height=30, halign="left"))
        self.status.text = f"Source: {result.get('source', 'api')}"
    
    def show_error(self, msg):
        self.status.text = f"Error: {msg}"


if __name__ == "__main__":
    YinYinTestApp().run()
