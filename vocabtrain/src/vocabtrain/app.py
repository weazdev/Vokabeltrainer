import toga
import json
import os
import random
import asyncio
import time
from datetime import datetime
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

class VokabelTrainer(toga.App):
    def startup(self):
        self.data_path = os.path.join(self.paths.data, "vocabulary.json")
        self.load_data()
        
        self.current_lesson_name = None
        self.words_to_test = [] 
        self.failed_words = []  
        self.current_test_pair = None
        self.test_direction = "en_to_de"
        
        # Statistik
        self.total_words_count = 0
        self.correct_answers = 0
        self.mistakes = 0
        self.start_time = 0

        self.main_box = toga.Box(style=Pack(direction=COLUMN, padding=20))
        
        # Start Buttons - Padding für Klickfläche
        btn_enter = toga.Button("Enter new vocabulary", on_press=self.show_lesson_overview, style=Pack(margin=15, padding=20))
        btn_test = toga.Button("Test yourself", on_press=self.show_test_selection, style=Pack(margin=15, padding=20, background_color="#ffcc80"))

        self.main_box.add(btn_enter)
        self.main_box.add(btn_test)

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = self.main_box
        self.main_window.show()

    # --- DATEN LOGIK ---
    def load_data(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, "r") as f:
                data = json.load(f)
                self.lessons = data.get("lessons", {})
                self.history = data.get("history", [])
        else:
            self.lessons = {}
            self.history = []

    def save_data(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        data_to_save = {
            "lessons": self.lessons,
            "history": self.history
        }
        with open(self.data_path, "w") as f:
            json.dump(data_to_save, f, indent=4)

    # --- HILFSFUNKTIONEN FÜR ZEIT ---
    def _parse_duration(self, duration_str):
        try:
            parts = duration_str.replace('m', '').replace('s', '').split()
            return int(parts[0]) * 60 + int(parts[1])
        except:
            return 0

    def _seconds_to_str(self, seconds):
        return f"{seconds // 60}m {seconds % 60}s"

    # --- NAVIGATION ---
    def go_back_to_main(self, widget):
        self.main_window.content = self.main_box

    def show_lesson_overview(self, widget):
        overview_box = toga.Box(style=Pack(direction=COLUMN, padding=10))
        overview_box.add(toga.Label("Edit Lessons:", style=Pack(font_weight="bold", margin_bottom=10, font_size=20)))
        
        lessons_list_box = toga.Box(style=Pack(direction=COLUMN))
        for lesson_name in self.lessons.keys():
            lesson_btn = toga.Button(
                lesson_name, 
                on_press=lambda widget, name=lesson_name: self.open_lesson_editor(name), 
                style=Pack(margin=5, padding=15, background_color="#e3f2fd", color="#0d47a1")
            )
            lessons_list_box.add(lesson_btn)
            
        scroll_container = toga.ScrollContainer(content=lessons_list_box, style=Pack(flex=1))
        overview_box.add(scroll_container)
        
        button_box = toga.Box(style=Pack(direction=COLUMN, margin_top=10))
        btn_new_lesson = toga.Button("New Lesson", on_press=self.show_create_lesson_box, style=Pack(margin_bottom=10, padding=15, background_color="#c8e6c9", color="#1b5e20"))
        btn_back = toga.Button("Back to Menu", on_press=self.go_back_to_main, style=Pack(margin_bottom=10, padding=15))
        
        button_box.add(btn_new_lesson)
        button_box.add(btn_back)
        overview_box.add(button_box)
        
        self.main_window.content = overview_box

    # --- TEST MODUS ---
    def show_test_selection(self, widget):
        selection_box = toga.Box(style=Pack(direction=COLUMN, padding=10))
        selection_box.add(toga.Label("Select Lesson to Test:", style=Pack(font_weight="bold", margin_bottom=10, font_size=20)))
        
        self.direction_select = toga.Selection(items=["English -> German", "German -> English"], style=Pack(margin_bottom=10, height=50))
        selection_box.add(self.direction_select)

        # Liste der Lessons
        lessons_list_box = toga.Box(style=Pack(direction=COLUMN))
        for lesson_name in self.lessons.keys():
            if self.lessons[lesson_name]:
                lesson_btn = toga.Button(
                    lesson_name, 
                    on_press=self.prepare_test,
                    style=Pack(margin=5, padding=15, background_color="#fff9c4", color="#f57f17")
                )
                lesson_btn.lesson_name = lesson_name 
                lessons_list_box.add(lesson_btn)
        
        scroll_container = toga.ScrollContainer(content=lessons_list_box, style=Pack(flex=1))
        selection_box.add(scroll_container)
        
        # --- ROBUSTE BUTTONS DIREKT IM LAYOUT ---
        btn_stats = toga.Button("Stats", on_press=self.show_stats_selection, style=Pack(margin_top=10, padding=15, background_color="#b3e5fc"))
        btn_delete = toga.Button("Delete Lesson", on_press=self.show_delete_dialog, style=Pack(margin_top=10, padding=15, background_color="#ff8a80", color="#b71c1c"))
        btn_back = toga.Button("Back to Menu", on_press=self.go_back_to_main, style=Pack(margin_top=10, padding=15))
        
        selection_box.add(btn_stats)
        selection_box.add(btn_delete)
        selection_box.add(btn_back)
        
        self.main_window.content = selection_box

    def prepare_test(self, widget):
        lesson_name = widget.lesson_name
        direction_text = self.direction_select.value
        if direction_text == "English -> German":
            self.test_direction = "en_to_de"
        else:
            self.test_direction = "de_to_en"
        self.start_test(lesson_name)

    # --- STATISTIK ---
    def show_stats_selection(self, widget):
        # Zeige scrollbare Liste der Lektionen
        stats_box = toga.Box(style=Pack(direction=COLUMN, padding=10))
        stats_box.add(toga.Label("Select lesson for stats:", style=Pack(font_weight="bold", margin_bottom=10, font_size=18)))
        
        lessons_list_box = toga.Box(style=Pack(direction=COLUMN))
        for lesson_name in self.lessons.keys():
            lesson_btn = toga.Button(
                lesson_name,
                on_press=lambda widget, name=lesson_name: self.display_stats(name),
                style=Pack(margin=5, padding=15, background_color="#e1f5fe")
            )
            lessons_list_box.add(lesson_btn)
            
        scroll_container = toga.ScrollContainer(content=lessons_list_box, style=Pack(flex=1))
        stats_box.add(scroll_container)
        
        btn_back = toga.Button("Cancel", on_press=self.show_test_selection, style=Pack(margin_top=10, padding=15))
        stats_box.add(btn_back)
        
        self.main_window.content = stats_box

    def display_stats(self, lesson_name):
        # Aufgerufen durch Button-Klick mit lesson_name
        lesson_history = [h for h in self.history if h['lesson'] == lesson_name]
        
        if not lesson_history:
            self.main_window.info_dialog(f"Stats: {lesson_name}", "No test data available for this lesson yet.")
            self.show_test_selection(None)
            return

        total_tests = len(lesson_history)
        total_correct = sum(h['correct'] for h in lesson_history)
        total_mistakes = sum(h['mistakes'] for h in lesson_history)
        
        total_seconds = sum(self._parse_duration(h['duration']) for h in lesson_history)
        avg_duration = self._seconds_to_str(total_seconds // total_tests)
        
        stats_msg = (f"Stats for '{lesson_name}':\n\n"
                     f"Total tests taken: {total_tests}\n"
                     f"Total correct: {total_correct}\n"
                     f"Total mistakes: {total_mistakes}\n"
                     f"Avg. duration: {avg_duration}")
        
        self.main_window.info_dialog("Lesson Statistics", stats_msg)
        self.show_test_selection(None)

    # --- LÖSCH LOGIK ---
    def show_delete_dialog(self, widget):
        # Zeige scrollbare Liste der Lektionen zum Löschen
        delete_box = toga.Box(style=Pack(direction=COLUMN, padding=10))
        delete_box.add(toga.Label("Select lesson to DELETE:", style=Pack(font_weight="bold", margin_bottom=10, font_size=18, color="#c62828")))
        
        lessons_list_box = toga.Box(style=Pack(direction=COLUMN))
        for lesson_name in self.lessons.keys():
            lesson_btn = toga.Button(
                lesson_name,
                on_press=lambda widget, name=lesson_name: self.confirm_delete(name),
                style=Pack(margin=5, padding=15, background_color="#ffcdd2", color="#b71c1c")
            )
            lessons_list_box.add(lesson_btn)
            
        scroll_container = toga.ScrollContainer(content=lessons_list_box, style=Pack(flex=1))
        delete_box.add(scroll_container)
        
        btn_back = toga.Button("Cancel", on_press=self.show_test_selection, style=Pack(margin_top=10, padding=15))
        delete_box.add(btn_back)
        
        self.main_window.content = delete_box

    def confirm_delete(self, lesson_name):
        self.main_window.question_dialog(
            "Confirm Delete", 
            f"Are you sure you want to delete '{lesson_name}'?\nThis cannot be undone.",
            on_result=lambda widget, result: self.perform_delete(lesson_name, result)
        )

    def perform_delete(self, lesson_name, result):
        if result:
            del self.lessons[lesson_name]
            self.history = [h for h in self.history if h['lesson'] != lesson_name]
            self.save_data()
            self.main_window.info_dialog("Deleted", f"Lesson '{lesson_name}' and its history was deleted.")
            self.show_test_selection(None)
    # -------------------

    def start_test(self, lesson_name):
        self.current_lesson_name = lesson_name
        self.words_to_test = list(self.lessons[lesson_name])
        random.shuffle(self.words_to_test)
        self.failed_words = []
        
        self.total_words_count = len(self.words_to_test)
        self.correct_answers = 0
        self.mistakes = 0
        self.start_time = time.time()
        self.next_test_pair()

    def get_formatted_duration(self):
        duration = int(time.time() - self.start_time)
        return self._seconds_to_str(duration)

    def next_test_pair(self):
        if not self.words_to_test:
            if self.failed_words:
                self.words_to_test = self.failed_words
                self.failed_words = []
                random.shuffle(self.words_to_test)
            else:
                # Vergleich der Dauer
                current_duration_str = self.get_formatted_duration()
                current_seconds = self._parse_duration(current_duration_str)
                
                lesson_history = [h for h in self.history if h['lesson'] == self.current_lesson_name]
                comparison_msg = ""
                if lesson_history:
                    total_seconds = sum(self._parse_duration(h['duration']) for h in lesson_history)
                    avg_seconds = total_seconds // len(lesson_history)
                    diff = current_seconds - avg_seconds
                    
                    if diff > 0:
                        comparison_msg = f"\n{self._seconds_to_str(diff)} slower than average."
                    elif diff < 0:
                        comparison_msg = f"\n{self._seconds_to_str(abs(diff))} faster than average!"
                    else:
                        comparison_msg = "\nExactly average time."
                
                self.save_test_history()
                
                msg = (f"Completed!\n"
                       f"Duration: {current_duration_str}{comparison_msg}\n"
                       f"Correct: {self.correct_answers}\n"
                       f"Mistakes: {self.mistakes}")
                self.main_window.info_dialog("Test Finished", msg)
                self.show_test_selection(None)
                return

        self.current_test_pair = self.words_to_test.pop()
        self.test_box = toga.Box(style=Pack(direction=COLUMN, padding=10))
        
        stats_text = (f"Remaining: {len(self.words_to_test) + len(self.failed_words) + 1} | "
                      f"Correct: {self.correct_answers} | "
                      f"Mistakes: {self.mistakes} | "
                      f"Time: {self.get_formatted_duration()}")
        
        self.test_box.add(toga.Label(stats_text, style=Pack(text_align="center", font_size=12, margin_bottom=10)))
        self.test_box.add(toga.Label(f"Lesson: {self.current_lesson_name}", style=Pack(font_size=14, text_align="center")))
        
        if self.test_direction == "en_to_de":
            question_word = self.current_test_pair['en']
            placeholder_text = "German"
        else:
            question_word = self.current_test_pair['de']
            placeholder_text = "English"
        
        self.test_box.add(toga.Label("Translate:", style=Pack(font_size=18, padding_top=10, text_align="center")))
        word_label = toga.Label(question_word, style=Pack(font_size=28, font_weight="bold", text_align="center", padding=15))
        self.test_box.add(word_label)
        
        # --- HÖHE DES EINGABEFELDES (height=80) ---
        self.test_input = toga.TextInput(placeholder=placeholder_text, style=Pack(height=80, font_size=24, padding_bottom=10))
        self.test_box.add(self.test_input)
        self.test_input.focus()
        
        self.btn_check = toga.Button("Check", on_press=self.check_answer, style=Pack(margin_top=15, padding=15, background_color="#2196f3", color="#FFFFFF"))
        self.test_box.add(self.btn_check)
        
        # --- ANZEIGE-LABELS UNTER BUTTON ---
        self.feedback_status = toga.Label("", style=Pack(font_size=22, font_weight="bold", padding_top=10, text_align="center"))
        self.feedback_details = toga.Label("", style=Pack(font_size=18, text_align="center"))
        
        self.test_box.add(self.feedback_status)
        self.test_box.add(self.feedback_details)
        
        self.main_window.content = self.test_box

    # --- HISTORIE ---
    def save_test_history(self):
        history_entry = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "lesson": self.current_lesson_name,
            "total_words": self.total_words_count,
            "correct": self.correct_answers,
            "mistakes": self.mistakes,
            "duration": self.get_formatted_duration()
        }
        self.history.append(history_entry)
        self.save_data()
    # --------------------------------

    # --- Async Funktion für nicht-blockierendes Feedback ---
    async def check_answer(self, widget):
        user_answer = self.test_input.value.strip()
        
        if self.test_direction == "en_to_de":
            correct_answer = self.current_test_pair['de'].strip()
            display_q = self.current_test_pair['en']
            display_a = correct_answer
        else:
            correct_answer = self.current_test_pair['en'].strip()
            display_q = self.current_test_pair['de']
            display_a = correct_answer

        self.btn_check.enabled = False
        self.test_input.enabled = False
        
        is_correct = user_answer.lower() == correct_answer.lower()
        
        # --- FARBIGE RÜCKMELDUNG ---
        feedback_details_text = f"{display_q} -> {display_a}"
        
        if is_correct:
            self.correct_answers += 1
            self.feedback_status.text = "Correct"
            self.feedback_status.style.color = "#2e7d32" 
            self.feedback_details.text = feedback_details_text
        else:
            self.mistakes += 1
            self.feedback_status.text = "Mistake"
            self.feedback_status.style.color = "#c62828" 
            self.feedback_details.text = feedback_details_text
            self.failed_words.append(self.current_test_pair)
        
        # --- Asynchrones Warten ---
        await asyncio.sleep(1.5) 
        
        # Rücksetzen für nächste Runde
        self.feedback_status.text = ""
        self.feedback_details.text = ""
        self.test_input.enabled = True
        self.btn_check.enabled = True
        self.next_test_pair()

    # --- EDITOR ---
    def show_create_lesson_box(self, widget):
        create_box = toga.Box(style=Pack(direction=COLUMN, padding=20))
        create_box.add(toga.Label("Enter new lesson name:", style=Pack(margin_bottom=10, font_size=18)))
        
        self.lesson_name_input = toga.TextInput(placeholder="e.g. Lesson 1", style=Pack(height=60, font_size=18))
        create_box.add(self.lesson_name_input)
        
        btn_confirm = toga.Button("Create", on_press=self.confirm_new_lesson, style=Pack(margin_top=15, padding=15, background_color="#c8e6c9"))
        btn_cancel = toga.Button("Cancel", on_press=self.show_lesson_overview, style=Pack(margin_top=10, padding=15))
        
        create_box.add(btn_confirm)
        create_box.add(btn_cancel)
        
        self.main_window.content = create_box

    def confirm_new_lesson(self, widget):
        name = self.lesson_name_input.value.strip()
        if name and name not in self.lessons:
            self.lessons[name] = []
            self.save_data()
            self.open_lesson_editor(name)
        elif name in self.lessons:
            self.main_window.info_dialog("Error", "Lesson already exists!")
        else:
            self.main_window.info_dialog("Error", "Name cannot be empty!")

    def open_lesson_editor(self, lesson_name):
        self.current_lesson_name = lesson_name
        editor_box = toga.Box(style=Pack(direction=COLUMN, padding=10))
        editor_box.add(toga.Label(f"Editing: {lesson_name}", style=Pack(font_weight="bold", margin_bottom=10, font_size=18)))
        
        input_box = toga.Box(style=Pack(direction=ROW, padding=5))
        self.input_en = toga.TextInput(placeholder="English", style=Pack(flex=1, margin_right=5, height=60, font_size=18))
        self.input_de = toga.TextInput(placeholder="German", style=Pack(flex=1, margin_right=5, height=60, font_size=18))
        
        self.input_de.on_confirm = self.add_vocabulary_to_lesson
        btn_save_vocab = toga.Button("Enter", on_press=self.add_vocabulary_to_lesson, style=Pack(color="#FFFFFF", background_color="#2196f3", padding=15))
        
        input_box.add(self.input_en)
        input_box.add(self.input_de)
        input_box.add(btn_save_vocab)
        
        self.vocab_display = toga.MultilineTextInput(readonly=True, style=Pack(flex=1, margin_top=10, font_size=16))
        self.refresh_vocab_display()
        
        btn_back = toga.Button("Back to List Overview", on_press=self.show_lesson_overview, style=Pack(margin_top=10, padding=15))
        
        editor_box.add(input_box)
        editor_box.add(toga.Label("Current Vocabulary:", style=Pack(margin_top=10, font_weight="bold")))
        editor_box.add(self.vocab_display)
        editor_box.add(btn_back)
        
        self.main_window.content = editor_box

    def refresh_vocab_display(self):
        text = ""
        for vocab in self.lessons[self.current_lesson_name]:
            text += f"{vocab['en']} - {vocab['de']}\n"
        self.vocab_display.value = text

    def add_vocabulary_to_lesson(self, widget):
        en_word = self.input_en.value
        de_word = self.input_de.value
        if en_word and de_word:
            new_vocab = {"en": en_word, "de": de_word}
            self.lessons[self.current_lesson_name].append(new_vocab)
            self.save_data()
            self.refresh_vocab_display()
            self.input_en.value = ""
            self.input_de.value = ""
            self.input_en.focus()
        else:
            self.main_window.info_dialog("Error", "Please fill in both fields!")

def main():
    return VokabelTrainer()