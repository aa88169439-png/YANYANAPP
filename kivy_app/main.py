import sys, os, threading, traceback

# Crash log for Android
_crash_log = None
try:
    if "ANDROID_PRIVATE" in os.environ:
        _crash_log = open(os.path.join(os.environ["ANDROID_PRIVATE"], "crash.log"), "w")
        sys.stderr = _crash_log
except Exception:
    pass

def _log_exception(exc_type, exc_val, exc_tb):
    msg = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
    if _crash_log:
        _crash_log.write(msg + "\n")
        _crash_log.flush()
sys.excepthook = _log_exception

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.togglebutton import ToggleButton
from kivy.clock import Clock
from kivy.metrics import dp

from api.translator import translate, TranslatorError, CATEGORY_MAP
from database.offline_database import init_offline_db
from database.database import init_db as init_vocab_db, save_word, get_all_words, search_words, delete_word
from config.config import load_config, save_config

INIT_DONE = False
init_offline_db()
init_vocab_db()
INIT_DONE = True

MODES = ["daily", "anime", "movie", "game", "internet", "formal"]
MODE_LABELS = ["Daily", "Anime", "Movie", "Game", "Internet", "Formal"]


class NavButton(Button):
    pass


class TranslateScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_result = None
        self.current_text = ""
        self.selected_mode = "daily"
        layout = BoxLayout(orientation="vertical", spacing=6, padding=10)

        # Mode row
        mode_row = BoxLayout(size_hint_y=None, height=45, spacing=4)
        self.mode_btns = {}
        for key, label in zip(MODES, MODE_LABELS):
            btn = ToggleButton(text=label, group="mode", size_hint_x=None, width=dp(80))
            btn.bind(on_press=lambda x, k=key: self._set_mode(k))
            mode_row.add_widget(btn)
            self.mode_btns[key] = btn
        self.mode_btns["daily"].state = "down"
        layout.add_widget(mode_row)

        self.input = TextInput(hint_text="Type English here...", multiline=False, size_hint_y=None, height=50)
        layout.add_widget(self.input)

        self.trans_btn = Button(text="Translate", size_hint_y=None, height=50)
        self.trans_btn.bind(on_press=lambda x: self.do_translate())
        layout.add_widget(self.trans_btn)

        self.status = Label(text="", size_hint_y=None, height=25)
        layout.add_widget(self.status)

        self.scroll = ScrollView()
        self.output = GridLayout(cols=1, spacing=4, size_hint_y=None)
        self.output.bind(minimum_height=self.output.setter("height"))
        self.scroll.add_widget(self.output)
        layout.add_widget(self.scroll)

        self.save_btn = Button(text="Save to Vocabulary", size_hint_y=None, height=0, opacity=0)
        self.save_btn.bind(on_press=lambda x: self.save_vocab())
        layout.add_widget(self.save_btn)

        self.add_widget(layout)

    def _set_mode(self, key):
        self.selected_mode = key

    def do_translate(self):
        text = self.input.text.strip()
        if not text:
            return
        self.current_text = text
        self.status.text = "Translating..."
        self.trans_btn.disabled = True
        threading.Thread(target=self._translate_thread, daemon=True).start()

    def _translate_thread(self):
        try:
            result = translate(self.current_text, self.selected_mode)
            Clock.schedule_once(lambda dt: self._show_result(result))
        except TranslatorError as e:
            Clock.schedule_once(lambda dt: self._show_error(str(e)))
        except Exception as e:
            Clock.schedule_once(lambda dt: self._show_error(f"Error: {e}"))

    def _show_result(self, result):
        self.current_result = result
        self.trans_btn.disabled = False
        self.output.clear_widgets()

        source = result.get("source", "api")
        mode_name = CATEGORY_MAP.get(self.selected_mode, self.selected_mode)
        self.status.text = f"[{source}] {mode_name}"

        rows = [
            ("Natural Chinese", result.get("natural_chinese", "")),
            ("Pinyin", result.get("pinyin", "")),
            ("Literal", result.get("literal_translation", "")),
            ("Internet", result.get("internet_expression", "")),
            ("ACG", result.get("acg_expression", "")),
            ("Culture", result.get("culture_note", "")),
            ("Example", result.get("example_sentence", "")),
            ("Translation", result.get("example_translation", "")),
        ]
        for label, val in rows:
            if val:
                self.output.add_widget(Label(text=f"[b]{label}[/b]", size_hint_y=None, height=20, markup=True, halign="left"))
                self.output.add_widget(Label(text=val, size_hint_y=None, height=30, halign="left", text_size=(self.width - 20, None)))

        self.save_btn.height = 50
        self.save_btn.opacity = 1

    def _show_error(self, msg):
        self.trans_btn.disabled = False
        self.status.text = msg

    def save_vocab(self):
        if not self.current_result:
            return
        r = self.current_result
        save_word({
            "english": self.current_text,
            "chinese": r.get("natural_chinese") or r.get("literal_translation") or "",
            "pinyin": r.get("pinyin", ""),
            "note": r.get("culture_note", ""),
            "example": r.get("example_sentence", ""),
        })
        self.save_btn.height = 0
        self.save_btn.opacity = 0
        self.status.text = "Saved!"


class VocabScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.query = ""
        layout = BoxLayout(orientation="vertical", spacing=6, padding=10)

        self.search = TextInput(hint_text="Search...", multiline=False, size_hint_y=None, height=45)
        self.search.bind(text=lambda x, y: self._do_search(y))
        layout.add_widget(self.search)

        self.scroll = ScrollView()
        self.list_layout = GridLayout(cols=1, spacing=4, size_hint_y=None)
        self.list_layout.bind(minimum_height=self.list_layout.setter("height"))
        self.scroll.add_widget(self.list_layout)
        layout.add_widget(self.scroll)

        btn = Button(text="Refresh", size_hint_y=None, height=45)
        btn.bind(on_press=lambda x: self._refresh())
        layout.add_widget(btn)

        self.add_widget(layout)

    def _do_search(self, text):
        self.query = text.strip()
        self._refresh()

    def _refresh(self):
        self.list_layout.clear_widgets()
        words = search_words(self.query) if self.query else get_all_words()
        if not words:
            self.list_layout.add_widget(Label(text="No words saved yet.", size_hint_y=None, height=40))
            return
        for w in words:
            box = BoxLayout(orientation="horizontal", size_hint_y=None, height=60, spacing=4)
            text_box = BoxLayout(orientation="vertical")
            text_box.add_widget(Label(text=f"{w.get('chinese', '')} - {w.get('english', '')}", halign="left", size_hint_y=None, height=25))
            if w.get("pinyin"):
                text_box.add_widget(Label(text=w["pinyin"], halign="left", size_hint_y=None, height=20, font_size=12))
            box.add_widget(text_box)
            del_btn = Button(text="X", size_hint_x=None, width=40)
            wid = w["id"]
            del_btn.bind(on_press=lambda x, wid=wid: self._delete(wid))
            box.add_widget(del_btn)
            self.list_layout.add_widget(box)

    def _delete(self, wid):
        delete_word(wid)
        self._refresh()


class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", spacing=8, padding=10)

        cfg = load_config()
        layout.add_widget(Label(text="API Settings", size_hint_y=None, height=40, bold=True))

        layout.add_widget(Label(text="API Key", size_hint_y=None, height=20, font_size=12))
        self.key_input = TextInput(text=cfg.get("api_key", ""), multiline=False, size_hint_y=None, height=45, password=True)
        layout.add_widget(self.key_input)

        layout.add_widget(Label(text="API URL", size_hint_y=None, height=20, font_size=12))
        self.url_input = TextInput(text=cfg.get("api_url", ""), multiline=False, size_hint_y=None, height=45)
        layout.add_widget(self.url_input)

        layout.add_widget(Label(text="Model", size_hint_y=None, height=20, font_size=12))
        self.model_input = TextInput(text=cfg.get("model", ""), multiline=False, size_hint_y=None, height=45)
        layout.add_widget(self.model_input)

        btn = Button(text="Save Settings", size_hint_y=None, height=50)
        btn.bind(on_press=lambda x: self._save())
        layout.add_widget(btn)

        self.msg = Label(text="", size_hint_y=None, height=30)
        layout.add_widget(self.msg)

        layout.add_widget(Label(text="Default: manyou.ink / gpt-5.4", size_hint_y=None, height=30, font_size=11))

        self.add_widget(layout)

    def _save(self):
        save_config({
            "api_key": self.key_input.text,
            "api_url": self.url_input.text,
            "model": self.model_input.text,
        })
        self.msg.text = "Saved!"


class YinYinApp(App):
    def build(self):
        self.title = "YinYin"
        root = BoxLayout(orientation="vertical")

        sm = ScreenManager()
        sm.add_widget(TranslateScreen(name="translate"))
        sm.add_widget(VocabScreen(name="vocab"))
        sm.add_widget(SettingsScreen(name="settings"))
        root.add_widget(sm)

        nav = BoxLayout(size_hint_y=None, height=50, spacing=2, padding=[10, 5])
        nav_btns = [
            ("Translate", "translate"),
            ("Vocab", "vocab"),
            ("Settings", "settings"),
        ]
        for label, screen in nav_btns:
            btn = Button(text=label)
            btn.bind(on_press=lambda x, s=screen: sm.current = s)
            nav.add_widget(btn)
        root.add_widget(nav)

        return root


if __name__ == "__main__":
    try:
        YinYinApp().run()
    except Exception as e:
        if _crash_log:
            _crash_log.write(f"FATAL: {e}\n{traceback.format_exc()}\n")
            _crash_log.flush()
        raise
