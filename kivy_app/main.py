import sys, os, threading, traceback

# Crash catcher for Android
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
        _crash_log.write(msg)
        _crash_log.flush()

sys.excepthook = _log_exception

from kivy.config import Config
Config.set("kivy", "window_icon", "")
Config.set("kivy", "exit_on_escape", "0")

from kivy.lang import Builder
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.core.text import LabelBase
from kivymd.app import MDApp
from kivymd.uix.bottomnavigation import MDBottomNavigation, MDBottomNavigationItem
from kivymd.uix.textfield import MDTextField
from kivymd.uix.chip import MDChip
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.list import OneLineIconListItem, ThreeLineListItem, IconRightWidget
from kivymd.uix.label import MDLabel
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.snackbar import MDSnackbar
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.card import MDCard
from api.translator import translate, TranslatorError, CATEGORY_MAP
from database.offline_database import init_offline_db
from database.database import init_db as init_vocab_db, save_word, get_all_words, search_words, delete_word
from config.config import load_config, save_config

KV = """
<ResultCard@MDCard>
    size_hint_y: None
    height: self.minimum_height + dp(16)
    padding: dp(12)
    spacing: dp(4)
    orientation: "vertical"
    md_bg_color: self.theme_cls.primaryContainerColor if self.highlight else self.theme_cls.surfaceContainerColor
    highlight: False
    radius: [dp(8)]
    ML: 16
    MR: 16
    
    MDLabel:
        text: root.label_text
        font_size: dp(12)
        theme_text_color: "Secondary"
        size_hint_y: None
        height: dp(16)
    MDLabel:
        id: value_lbl
        text: root.value_text
        font_size: dp(16) if not root.highlight else dp(20)
        bold: root.highlight
        theme_text_color: "Primary"
        size_hint_y: None
        adaptive_height: True
    MDLabel:
        id: sub_lbl
        text: root.sub_text
        font_size: dp(13)
        theme_text_color: "Hint"
        size_hint_y: None
        height: dp(18) if root.sub_text else dp(0)
        opacity: 1 if root.sub_text else 0

BoxLayout:
    orientation: "vertical"
    
    MDTopAppBar:
        title: "娲囨磭涓撶敤"
        md_bg_color: app.theme_cls.primaryColor
        specific_text_color: app.theme_cls.surfaceColor
    
    MDBottomNavigation:
        id: bottom_nav
        panel_color: app.theme_cls.surfaceContainerColor
        
        MDBottomNavigationItem:
            name: "translate"
            text: "缈昏瘧"
            icon: "translate-variant"
            
            BoxLayout:
                orientation: "vertical"
                
                ScrollView:
                    MDBoxLayout:
                        orientation: "vertical"
                        padding: dp(12)
                        spacing: dp(8)
                        adaptive_height: True
                        
                        MDTextField:
                            id: input_field
                            hint_text: "Type English here..."
                            mode: "outlined"
                            multiline: True
                            max_height: dp(150)
                            size_hint_y: None
                            height: dp(80)
                        
                        MDBoxLayout:
                            id: mode_row
                            size_hint_y: None
                            height: dp(40)
                            spacing: dp(6)
                            adaptive_width: True
                        
                        MDRaisedButton:
                            id: translate_btn
                            text: "Translate"
                            pos_hint: {"center_x": 0.5}
                            size_hint_x: 0.8
                            size_hint_y: None
                            height: dp(48)
                            on_release: app.do_translate()
                        
                        MDBoxLayout:
                            id: loading_box
                            size_hint_y: None
                            height: dp(40) if self.opacity else dp(0)
                            opacity: 0
                            
                            MDSpinner:
                                size_hint: None, None
                                size: dp(24), dp(24)
                                pos_hint: {"center_x": 0.5, "center_y": 0.5}
                            MDLabel:
                                text: "Translating..."
                                halign: "center"
                                valign: "center"
                        
                        MDLabel:
                            id: error_label
                            size_hint_y: None
                            height: dp(0)
                            opacity: 0
                            theme_text_color: "Error"
                            halign: "center"
                        
                        MDBoxLayout:
                            id: result_header
                            size_hint_y: None
                            height: dp(0)
                            opacity: 0
                            spacing: dp(8)
                            MDLabel:
                                id: source_label
                                size_hint_x: None
                                width: dp(60)
                            MDLabel:
                                id: mode_label
                                theme_text_color: "Secondary"
                            MDLabel:
                                id: usage_label
                                theme_text_color: "Hint"
                                halign: "right"
                        
                        ScrollView:
                            size_hint_y: None
                            height: dp(400)
                            do_scroll_y: True
                            MDBoxLayout:
                                id: result_container
                                orientation: "vertical"
                                adaptive_height: True
                                spacing: dp(6)
                        
                        MDFlatButton:
                            id: save_btn
                            text: "Save to Vocabulary"
                            size_hint_y: None
                            height: dp(0)
                            opacity: 0
                            on_release: app.save_vocabulary()
        
        MDBottomNavigationItem:
            name: "vocabulary"
            text: "鐢熻瘝鏈?
            icon: "book-open-variant"
            
            BoxLayout:
                orientation: "vertical"
                
                MDTextField:
                    id: search_field
                    hint_text: "Search words..."
                    mode: "outlined"
                    size_hint_y: None
                    height: dp(56)
                    on_text: app.search_vocabulary(self.text)
                
                ScrollView:
                    MDList:
                        id: vocab_list
        
        MDBottomNavigationItem:
            name: "settings"
            text: "璁剧疆"
            icon: "cog"
            
            ScrollView:
                MDBoxLayout:
                    orientation: "vertical"
                    padding: dp(16)
                    spacing: dp(12)
                    adaptive_height: True
                    
                    MDTextField:
                        id: api_key_field
                        hint_text: "API Key"
                        mode: "outlined"
                        password: True
                    
                    MDTextField:
                        id: api_url_field
                        hint_text: "API URL"
                        mode: "outlined"
                    
                    MDTextField:
                        id: model_field
                        hint_text: "Model"
                        mode: "outlined"
                    
                    MDRaisedButton:
                        text: "Save Settings"
                        size_hint_x: 0.8
                        pos_hint: {"center_x": 0.5}
                        size_hint_y: None
                        height: dp(48)
                        on_release: app.save_settings()
                    
                    MDLabel:
                        text: "Default:"
                        theme_text_color: "Secondary"
                        font_size: dp(12)
                        adaptive_height: True
                    
                    MDLabel:
                        text: "URL: https://manyou.ink/v1/chat/completions"
                        theme_text_color: "Hint"
                        font_size: dp(11)
                        adaptive_height: True
                    
                    MDLabel:
                        text: "Model: gpt-5.4"
                        theme_text_color: "Hint"
                        font_size: dp(11)
                        adaptive_height: True
"""


class YinYinApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_result = None
        self.current_text = ""
        self.selected_mode = "daily"
        self.mode_chips = {}
        self.result_cards = {}

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Red"
        self.theme_cls.primary_hue = "600"
        
        init_offline_db()
        init_vocab_db()
        
        try:
            root = Builder.load_string(KV)
        except Exception as e:
            if _crash_log:
                _crash_log.write(f"KV Load Error: {e}\n{traceback.format_exc()}")
                _crash_log.flush()
            raise
        
        self._build_mode_chips(root)
        self._build_result_cards(root)
        self._load_settings(root)
        
        self.root_widget = root
        return root

    def _build_mode_chips(self, root):
        row = root.ids.mode_row
        modes = [("daily", "Daily"), ("anime", "Anime"), ("movie", "Movie"),
                 ("game", "Game"), ("internet", "Internet"), ("formal", "Formal")]
        for key, label in modes:
            chip = MDChip(label=label, pos_hint={"center_y": 0.5}, check=True)
            chip.bind(active=lambda c, active, k=key: self._on_mode_select(k, active))
            row.add_widget(chip)
            self.mode_chips[key] = chip
        if self.mode_chips:
            self.mode_chips["daily"].active = True

    def _build_result_cards(self, root):
        container = root.ids.result_container
        fields = [
            ("literal_translation", "Literal", False),
            ("natural_chinese", "Natural Chinese", True),
            ("internet_expression", "Internet Slang", False),
            ("acg_expression", "ACG Expression", False),
            ("culture_note", "Culture Note", False),
            ("example_sentence", "Example", False),
        ]
        for key, label, highlight in fields:
            card = Builder.load_string(f"""
ResultCard:
    label_text: "{label}"
    value_text: ""
    sub_text: ""
    highlight: {"True" if highlight else "False"}
""")
            card.id = key
            container.add_widget(card)
            self.result_cards[key] = card

    def _load_settings(self, root):
        cfg = load_config()
        root.ids.api_key_field.text = cfg.get("api_key", "")
        root.ids.api_url_field.text = cfg.get("api_url", "")
        root.ids.model_field.text = cfg.get("model", "")

    def _on_mode_select(self, key, active):
        if active:
            self.selected_mode = key
            for k, chip in self.mode_chips.items():
                if k != key and chip.active:
                    chip.active = False

    def do_translate(self):
        text = self.root_widget.ids.input_field.text.strip()
        if not text:
            self._show_error("Please enter text.")
            return

        self.current_text = text
        self._set_loading(True)
        self._clear_error()

        threading.Thread(target=self._translate_thread, daemon=True).start()

    def _translate_thread(self):
        try:
            result = translate(self.current_text, self.selected_mode)
            Clock.schedule_once(lambda dt: self._show_result(result))
        except TranslatorError as e:
            Clock.schedule_once(lambda dt, msg=str(e): self._show_error(msg))
        except Exception as e:
            Clock.schedule_once(lambda dt, msg=f"Error: {e}": self._show_error(msg))

    def _show_result(self, result):
        self._set_loading(False)
        self.current_result = result
        root = self.root_widget

        root.ids.result_header.height = dp(24)
        root.ids.result_header.opacity = 1

        source = result.get("source", "api")
        sl = root.ids.source_label
        if source == "cache":
            sl.text = "[Cache]"
            sl.theme_text_color = "Custom"
            sl.text_color = self.theme_cls.successColor
        else:
            sl.text = "[AI]"
            sl.theme_text_color = "Custom"
            sl.text_color = self.theme_cls.primaryLight

        root.ids.mode_label.text = result.get("mode_label", CATEGORY_MAP.get(self.selected_mode, ""))
        usage = result.get("usage", {})
        root.ids.usage_label.text = f"{usage.get('total_tokens', '')} tokens" if usage and usage.get("total_tokens") else ""

        for key, card in self.result_cards.items():
            card.value_text = result.get(key, "") or ""
            card.sub_text = ""

        if result.get("pinyin"):
            self.result_cards["natural_chinese"].sub_text = f"[ {result['pinyin']} ]"
        if result.get("example_translation"):
            self.result_cards["example_sentence"].sub_text = result["example_translation"]

        root.ids.save_btn.height = dp(48)
        root.ids.save_btn.opacity = 1

    def _set_loading(self, loading):
        root = self.root_widget
        box = root.ids.loading_box
        btn = root.ids.translate_btn
        box.opacity = 1 if loading else 0
        box.height = dp(40) if loading else dp(0)
        btn.disabled = loading
        btn.text = "Translating..." if loading else "Translate"

    def _show_error(self, msg):
        self._set_loading(False)
        root = self.root_widget
        root.ids.error_label.text = msg
        root.ids.error_label.height = dp(100)
        root.ids.error_label.opacity = 1
        Clock.schedule_once(lambda dt: self._clear_error(), 5)

    def _clear_error(self):
        root = self.root_widget
        root.ids.error_label.text = ""
        root.ids.error_label.height = dp(0)
        root.ids.error_label.opacity = 0

    def save_vocabulary(self):
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
        self.root_widget.ids.save_btn.height = dp(0)
        self.root_widget.ids.save_btn.opacity = 0
        MDSnackbar(text="Saved to vocabulary!").open()

    def search_vocabulary(self, text):
        self._refresh_vocab_list(text.strip())

    def _refresh_vocab_list(self, query=""):
        words = search_words(query) if query else get_all_words()
        vl = self.root_widget.ids.vocab_list
        vl.clear_widgets()

        if not words:
            vl.add_widget(OneLineIconListItem(text="No words saved yet."))
            return

        for w in words:
            item = ThreeLineListItem(
                text=f"[b]{w.get('chinese', '')}[/b]    {w.get('english', '')}",
                secondary_text=w.get("pinyin", ""),
                tertiary_text=w.get("example", ""),
                markup=True,
            )
            item.add_widget(IconRightWidget(
                icon="delete",
                on_release=lambda x, wid=w["id"]: self._delete_word(wid),
            ))
            vl.add_widget(item)

    def _delete_word(self, word_id):
        delete_word(word_id)
        self._refresh_vocab_list(self.root_widget.ids.search_field.text)
        MDSnackbar(text="Word deleted").open()

    def save_settings(self):
        root = self.root_widget
        save_config({
            "api_key": root.ids.api_key_field.text,
            "api_url": root.ids.api_url_field.text,
            "model": root.ids.model_field.text,
        })
        MDSnackbar(text="Settings saved!").open()


if __name__ == "__main__":
    try:
        YinYinApp().run()
    except Exception as e:
        if _crash_log:
            _crash_log.write(f"FATAL: {e}\n{traceback.format_exc()}")
            _crash_log.flush()
        raise
