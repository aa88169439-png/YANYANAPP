import sys, os, threading

from kivy.config import Config
Config.set("kivy", "window_icon", "")
Config.set("kivy", "exit_on_escape", "0")

from kivy.lang import Builder
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.bottomnavigation import MDBottomNavigation, MDBottomNavigationItem
from kivymd.uix.textfield import MDTextField
from kivymd.uix.chip import MDChip
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDRectangleFlatButton, MDRaisedButton, MDFlatButton
from kivymd.uix.list import OneLineIconListItem, TwoLineListItem, ThreeLineListItem, IconRightWidget
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.label import MDLabel
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.snackbar import MDSnackbar
from kivymd.uix.dialog import MDDialog
from kivymd.uix.toolbar import MDTopAppBar

from api.translator import translate, TranslatorError, CATEGORY_MAP
from database.offline_database import init_offline_db
from database.database import init_db as init_vocab_db, save_word, get_all_words, search_words, delete_word
from config.config import load_config, save_config

KV = """
<ResultCard@MDCard>:
    size_hint_y: None
    height: dp(60)
    padding: dp(12)
    spacing: dp(4)
    orientation: "vertical"
    md_bg_color: app.theme_cls.primaryContainerColor if self.highlight else app.theme_cls.surfaceContainerColor
    highlight: False
    adaptive_height: True
    radius: [dp(8)]
    
    MDLabel:
        text: root.label_text
        font_size: dp(12)
        theme_text_color: "Secondary"
        size_hint_y: None
        height: dp(16)
    MDLabel:
        id: value_label
        text: root.value_text
        font_size: dp(16) if not root.highlight else dp(20)
        bold: root.highlight
        theme_text_color: "Primary"
        size_hint_y: None
        adaptive_height: True
    MDLabel:
        id: sub_label
        text: root.sub_text
        font_size: dp(13)
        theme_text_color: "Hint"
        size_hint_y: None
        height: dp(18) if root.sub_text else dp(0)
        opacity: 1 if root.sub_text else 0

MDScreen:
    name: "translate"
    
    BoxLayout:
        orientation: "vertical"
        
        MDTopAppBar:
            title: "洇洇专用"
            md_bg_color: app.theme_cls.primaryColor
            specific_text_color: app.theme_cls.surfaceColor
        
        ScrollView:
            ScrollView:
                do_scroll_x: False
                BoxLayout:
                    orientation: "vertical"
                    padding: dp(12)
                    spacing: dp(8)
                    size_hint_y: None
                    height: self.minimum_height
                    adaptive_height: True
                    
                    MDTextField:
                        id: input_field
                        hint_text: "Type English here..."
                        mode: "outlined"
                        multiline: True
                        max_height: dp(150)
                        size_hint_y: None
                        height: dp(80)
                    
                    BoxLayout:
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
                    
                    BoxLayout:
                        id: loading_box
                        size_hint_y: None
                        height: dp(40)
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
                        text: ""
                        theme_text_color: "Error"
                        halign: "center"
                    
                    BoxLayout:
                        id: result_header
                        size_hint_y: None
                        height: dp(0)
                        opacity: 0
                        spacing: dp(8)
                        
                        MDLabel:
                            id: source_label
                            size_hint_x: None
                            width: dp(60)
                            text: ""
                        MDLabel:
                            id: mode_label
                            text: ""
                            theme_text_color: "Secondary"
                        MDLabel:
                            id: usage_label
                            text: ""
                            theme_text_color: "Hint"
                            halign: "right"
                    
                    ScrollView:
                        size_hint_y: None
                        height: dp(400)
                        do_scroll_y: True
                        BoxLayout:
                            id: result_container
                            orientation: "vertical"
                            size_hint_y: None
                            height: self.minimum_height
                            adaptive_height: True
                            spacing: dp(6)
                    
                    MDFlatButton:
                        id: save_btn
                        text: "Save to Vocabulary"
                        size_hint_y: None
                        height: dp(0)
                        opacity: 0
                        on_release: app.save_vocabulary()

MDScreen:
    name: "vocabulary"
    
    BoxLayout:
        orientation: "vertical"
        
        MDTopAppBar:
            title: "Vocabulary"
            md_bg_color: app.theme_cls.primaryColor
            specific_text_color: app.theme_cls.surfaceColor
        
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

MDScreen:
    name: "settings"
    
    BoxLayout:
        orientation: "vertical"
        
        MDTopAppBar:
            title: "Settings"
            md_bg_color: app.theme_cls.primaryColor
            specific_text_color: app.theme_cls.surfaceColor
        
        ScrollView:
            BoxLayout:
                orientation: "vertical"
                padding: dp(16)
                spacing: dp(12)
                size_hint_y: None
                height: self.minimum_height
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
                    size_hint_y: None
                    height: dp(20)
                
                MDLabel:
                    text: "URL: https://manyou.ink/v1/chat/completions"
                    theme_text_color: "Hint"
                    font_size: dp(11)
                    size_hint_y: None
                    height: dp(18)
                
                MDLabel:
                    text: "Model: gpt-5.4"
                    theme_text_color: "Hint"
                    font_size: dp(11)
                    size_hint_y: None
                    height: dp(18)
"""


class TranslateScreen(MDScreen):
    pass


class VocabularyScreen(MDScreen):
    pass


class SettingsScreen(MDScreen):
    pass


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
        
        root = Builder.load_string(KV)
        
        self._build_mode_chips(root)
        self._build_result_cards(root)
        self._load_settings(root)
        
        nav = MDBottomNavigation()
        nav.add_widget(self._nav_item(root, "translate", "Translate", "translate-variant"))
        nav.add_widget(self._nav_item(root, "vocabulary", "Vocabulary", "book-open-variant"))
        nav.add_widget(self._nav_item(root, "settings", "Settings", "cog"))
        
        main = BoxLayout(orientation="vertical")
        main.add_widget(root)
        main.add_widget(nav)
        
        self.root_screen = root
        
        return main

    def _nav_item(self, root, name, text, icon):
        screen = root
        return MDBottomNavigationItem(name=name, text=text, icon=icon)

    def _build_mode_chips(self, root):
        row = root.ids.mode_row
        modes = [("daily", "Daily"), ("anime", "Anime"), ("movie", "Movie"),
                 ("game", "Game"), ("internet", "Internet"), ("formal", "Formal")]
        for key, label in modes:
            chip = MDChip(
                label=label,
                pos_hint={"center_y": 0.5},
                check=True,
            )
            chip.bind(active=lambda c, active, k=key: self._on_mode_select(k, active))
            row.add_widget(chip)
            self.mode_chips[key] = chip
        if self.mode_chips:
            self.mode_chips["daily"].active = True

    def _build_result_cards(self, root):
        container = root.ids.result_container
        fields = [
            ("literal_translation", "Literal", False, ""),
            ("natural_chinese", "Natural Chinese", True, ""),
            ("internet_expression", "Internet Slang", False, ""),
            ("acg_expression", "ACG Expression", False, ""),
            ("culture_note", "Culture Note", False, ""),
            ("example_sentence", "Example", False, ""),
        ]
        for key, label, highlight, sub in fields:
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
        text = self.root_screen.ids.input_field.text.strip()
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

        root = self.root_screen
        result_header = root.ids.result_header
        result_header.height = dp(24)
        result_header.opacity = 1

        source = result.get("source", "api")
        source_label = root.ids.source_label
        if source == "cache":
            source_label.text = "[Cache]"
            source_label.theme_text_color = "Custom"
            source_label.text_color = self.theme_cls.successColor
        else:
            source_label.text = "[AI]"
            source_label.theme_text_color = "Custom"
            source_label.text_color = self.theme_cls.primaryLight

        root.ids.mode_label.text = result.get("mode_label", CATEGORY_MAP.get(self.selected_mode, ""))
        usage = result.get("usage", {})
        if usage and usage.get("total_tokens"):
            root.ids.usage_label.text = f"{usage['total_tokens']} tokens"
        else:
            root.ids.usage_label.text = ""

        for key, card in self.result_cards.items():
            card.value_text = result.get(key, "") or ""
            card.sub_text = ""

        if result.get("pinyin"):
            self.result_cards["natural_chinese"].sub_text = f"[ {result['pinyin']} ]"

        if result.get("example_translation"):
            self.result_cards["example_sentence"].sub_text = result["example_translation"]

        save_btn = root.ids.save_btn
        save_btn.height = dp(48)
        save_btn.opacity = 1

    def _set_loading(self, loading):
        box = self.root_screen.ids.loading_box
        btn = self.root_screen.ids.translate_btn
        if loading:
            box.opacity = 1
            box.height = dp(40)
            btn.disabled = True
            btn.text = "Translating..."
        else:
            box.opacity = 0
            box.height = dp(0)
            btn.disabled = False
            btn.text = "Translate"

    def _show_error(self, msg):
        self._set_loading(False)
        label = self.root_screen.ids.error_label
        label.text = msg
        label.height = dp(100)
        label.opacity = 1
        Clock.schedule_once(lambda dt: self._clear_error(), 5)

    def _clear_error(self):
        label = self.root_screen.ids.error_label
        label.text = ""
        label.height = dp(0)
        label.opacity = 0

    def save_vocabulary(self):
        if not self.current_result:
            return
        r = self.current_result
        wid = save_word({
            "english": self.current_text,
            "chinese": r.get("natural_chinese") or r.get("literal_translation") or "",
            "pinyin": r.get("pinyin", ""),
            "note": r.get("culture_note", ""),
            "example": r.get("example_sentence", ""),
        })
        self.root_screen.ids.save_btn.height = dp(0)
        self.root_screen.ids.save_btn.opacity = 0
        MDSnackbar(text="Saved to vocabulary!", pos_hint={"center_x": 0.5, "center_y": 0.1}).open()

    def search_vocabulary(self, text):
        self._refresh_vocab_list(text.strip())

    def on_pre_enter(self):
        if hasattr(self, "root_screen"):
            self._refresh_vocab_list()

    def _refresh_vocab_list(self, query=""):
        if query:
            words = search_words(query)
        else:
            words = get_all_words()

        vocab_list = self.root_screen.ids.vocab_list
        vocab_list.clear_widgets()

        for w in words:
            item = ThreeLineListItem(
                text=f"[b]{w.get('chinese', '')}[/b]    {w.get('english', '')}",
                secondary_text=w.get("pinyin", ""),
                tertiary_text=w.get("example", ""),
                markup=True,
            )
            delete_btn = IconRightWidget(
                icon="delete",
                on_release=lambda x, wid=w["id"]: self._delete_word(wid),
            )
            item.add_widget(delete_btn)
            vocab_list.add_widget(item)

        if not words:
            empty = OneLineIconListItem(text="No words saved yet.")
            vocab_list.add_widget(empty)

    def _delete_word(self, word_id):
        delete_word(word_id)
        self._refresh_vocab_list(self.root_screen.ids.search_field.text)
        MDSnackbar(text="Word deleted").open()

    def save_settings(self):
        root = self.root_screen
        save_config({
            "api_key": root.ids.api_key_field.text,
            "api_url": root.ids.api_url_field.text,
            "model": root.ids.model_field.text,
        })
        MDSnackbar(text="Settings saved!").open()


if __name__ == "__main__":
    YinYinApp().run()
