import tkinter as tk
import random
import jaconv
import time
import os
import json
import openai
from prompt import get_kadai_list_creation_prompt


def katakana_to_romaji(text):
    """Convert katakana characters to romaji using jaconv library"""
    try:
        # Use jaconv for the main conversion
        result = jaconv.kata2alphabet(text)

        # Replace any remaining full-width characters with half-width
        result = result.replace("ー", "-")
        result = result.replace("－", "-")  # Full-width minus
        result = result.replace("—", "-")  # Em dash
        result = result.replace("‐", "-")  # Hyphen

        return result

    except Exception as e:
        print(f"jaconv conversion failed: {e}")
        # Fall back to basic conversion
        pass


class VsTypingDojo:
    def __init__(self, root):
        self.root = root
        self.root.title("VS Typing Dojo")
        self.root.geometry("1000x780")
        self.root.configure(bg="#1a1a2e")

        # ゲーム変数（日本語のことわざ）
        self.default_words = [
            {"japanese": "犬も歩けば棒に当たる", "romaji": "inumoarukebabouniataru"},
            {"japanese": "猫に小判", "romaji": "nekonikoban"},
            {"japanese": "七転び八起き", "romaji": "nanakorobiyaoki"},
            {"japanese": "花より団子", "romaji": "hanayoridango"},
            {"japanese": "石の上にも三年", "romaji": "ishinouenimosannen"},
            {"japanese": "時は金なり", "romaji": "tokihakanenari"},
            {"japanese": "急がば回れ", "romaji": "isogabamaware"},
            {
                "japanese": "塵も積もれば山となる",
                "romaji": "chirimotsumorebayamatonaru",
            },
            {"japanese": "継続は力なり", "romaji": "keizokuhachikaranari"},
            {"japanese": "案ずるより産むが易し", "romaji": "anzuruyoriumugayasushi"},
            {"japanese": "一期一会", "romaji": "ichigoichie"},
            {"japanese": "温故知新", "romaji": "onkochishin"},
            {"japanese": "十人十色", "romaji": "juunintoiro"},
            {"japanese": "百聞は一見に如かず", "romaji": "hyakubunhaikkennishikazu"},
            {"japanese": "類は友を呼ぶ", "romaji": "ruihatomowoyobu"},
        ]

        self.words = self.default_words.copy()
        self.openai_client = None
        self.setup_openai()

        # ユーザータイプ選択（refresh_wordsより前に初期化）
        self.selected_user_type = "12歳"  # デフォルト値
        self.current_word_data = None
        self.current_romaji = ""

        # Player 1 (小文字)
        self.p1_score = 0
        self.p1_words_typed = 0
        self.p1_current_position = 0
        self.p1_correct_chars = 0
        self.p1_total_chars = 0
        self.p1_perfect_typing = True  # 現在の文章でパーフェクトタイピング中かどうか
        self.p1_perfect_count = 0  # パーフェクトタイピング回数

        # Player 2 (大文字)
        self.p2_score = 0
        self.p2_words_typed = 0
        self.p2_current_position = 0
        self.p2_correct_chars = 0
        self.p2_total_chars = 0
        self.p2_perfect_typing = True  # 現在の文章でパーフェクトタイピング中かどうか
        self.p2_perfect_count = 0  # パーフェクトタイピング回数

        # ゲーム共通
        self.start_time = 0
        self.game_active = False
        self.game_duration = 60  # デフォルト60秒間
        self.selected_duration = 60  # 選択可能な時間
        self.timer_job = None
        self.countdown_job = None
        self.countdown_value = 3

        # 使用済み文章の追跡（1ゲーム内で重複を防ぐ）
        self.used_sentences = set()

        self.setup_ui()
        self.hide_word()

    def setup_openai(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                self.openai_client = openai.OpenAI(api_key=api_key)
            except Exception as e:
                print(f"OpenAI setup failed: {e}")
                self.openai_client = None

    def generate_sentences_with_openai(self, user_type=None):
        """Generate sentences using the prompt from prompt.py with structured output"""
        if not self.openai_client:
            return []

        # デフォルトまたは選択されたユーザータイプを使用
        if user_type is None:
            user_type = self.selected_user_type

        try:
            prompt = get_kadai_list_creation_prompt(user_type)

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000,
            )

            content = response.choices[0].message.content.strip()

            print(response.choices[0].message.content)

            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()

            data = json.loads(content)
            sentences = data.get("sentences", [])

            # Convert to the format expected by the game
            words = []
            for item in sentences:
                sentence = item.get("sentence", "")
                katakana = item.get("katakana", "")
                romaji = katakana_to_romaji(katakana)

                if sentence and romaji:
                    words.append({"japanese": sentence, "romaji": romaji})

            return words

        except Exception as e:
            print(f"OpenAI sentence generation failed: {e}")
            return []

    def refresh_words(self):
        if self.openai_client:
            new_words = self.generate_sentences_with_openai()

            if new_words:
                self.words = new_words
                print(f"Added {len(new_words)} new words from OpenAI")
            else:
                self.words = self.default_words.copy()
                print("Using default words (OpenAI generation failed)")
        else:
            self.words = self.default_words.copy()
            print("Using default words (OpenAI not available)")

    def refresh_sentences_async(self):
        if hasattr(self, "refresh_sentences_button"):
            self.refresh_sentences_button.config(text="取得中...", state="disabled")

        def do_refresh():
            if self.openai_client:
                new_words = self.generate_sentences_with_openai()
                if new_words:
                    self.words = new_words + self.default_words
                    print(f"Added {len(new_words)} new sentences from OpenAI")
                else:
                    print("Sentence generation failed")

            if hasattr(self, "refresh_sentences_button"):
                self.refresh_sentences_button.config(text="新しい課題", state="normal")

        self.root.after(100, do_refresh)

    def setup_ui(self):
        # ゲームタイトル (最上部)
        title_frame = tk.Frame(self.root, bg="#1a1a2e", height=40)
        title_frame.pack(fill="x", pady=5)
        title_frame.pack_propagate(False)

        title_label = tk.Label(
            title_frame,
            text="VS Typing Dojo",
            font=("Arial", 18, "bold"),
            bg="#1a1a2e",
            fg="white",
        )
        title_label.pack(expand=True)

        # タイマー表示
        timer_frame = tk.Frame(self.root, bg="#1a1a2e", height=60)
        timer_frame.pack(fill="x", pady=5)
        timer_frame.pack_propagate(False)

        self.timer_label = tk.Label(
            timer_frame,
            text="",
            font=("Arial", 16, "bold"),
            bg="#1a1a2e",
            fg="#FFC107",
            justify="center",
        )
        self.timer_label.pack(expand=True)

        # Player 1 エリア
        p1_main_frame = tk.Frame(self.root, bg="#1a1a2e", height=200)
        p1_main_frame.pack(fill="x", pady=5)
        p1_main_frame.pack_propagate(False)

        # Player 1 タイトル
        tk.Label(
            p1_main_frame,
            text="PLAYER 1",
            font=("Arial", 14, "bold"),
            bg="#1a1a2e",
            fg="#4CAF50",
        ).pack(pady=2)

        # Player 1 スコア
        self.p1_score_label = tk.Label(
            p1_main_frame,
            text=f"スコア: {self.p1_score}",
            font=("Arial", 12, "bold"),
            bg="#1a1a2e",
            fg="#4CAF50",
        )
        self.p1_score_label.pack(pady=1)

        # Player 1 単語表示エリア
        p1_word_frame = tk.Frame(
            p1_main_frame, bg="#16213e", relief="ridge", bd=2, height=100
        )
        p1_word_frame.pack(pady=5, padx=50, fill="x")
        p1_word_frame.pack_propagate(False)

        self.p1_char_frame = tk.Frame(p1_word_frame, bg="#16213e")
        self.p1_char_frame.pack(expand=True)
        self.p1_char_labels = []

        # Player 1 統計
        self.p1_stats_label = tk.Label(
            p1_main_frame,
            font=("Arial", 10),
            bg="#1a1a2e",
            fg="#888",
        )
        self.p1_stats_label.pack(pady=1)

        # Player 2 エリア
        p2_main_frame = tk.Frame(self.root, bg="#1a1a2e", height=200)
        p2_main_frame.pack(fill="x", pady=5)
        p2_main_frame.pack_propagate(False)

        # Player 2 タイトル
        tk.Label(
            p2_main_frame,
            text="PLAYER 2",
            font=("Arial", 14, "bold"),
            bg="#1a1a2e",
            fg="#2196F3",
        ).pack(pady=2)

        # Player 2 スコア
        self.p2_score_label = tk.Label(
            p2_main_frame,
            text=f"スコア: {self.p2_score}",
            font=("Arial", 12, "bold"),
            bg="#1a1a2e",
            fg="#2196F3",
        )
        self.p2_score_label.pack(pady=1)

        # Player 2 単語表示エリア
        p2_word_frame = tk.Frame(
            p2_main_frame, bg="#16213e", relief="ridge", bd=2, height=100
        )
        p2_word_frame.pack(pady=5, padx=50, fill="x")
        p2_word_frame.pack_propagate(False)

        self.p2_char_frame = tk.Frame(p2_word_frame, bg="#16213e")
        self.p2_char_frame.pack(expand=True)
        self.p2_char_labels = []

        # Player 2 統計
        self.p2_stats_label = tk.Label(
            p2_main_frame,
            font=("Arial", 10),
            bg="#1a1a2e",
            fg="#888",
        )
        self.p2_stats_label.pack(pady=1)

        # 設定選択エリア（縦に配置、中央揃え）
        settings_frame = tk.Frame(self.root, bg="#1a1a2e")
        settings_frame.pack(fill="x", pady=10)

        # ゲーム時間選択エリア
        timer_section = tk.Frame(settings_frame, bg="#1a1a2e")
        timer_section.pack(pady=(5, 10))

        # ゲーム時間ラベル
        tk.Label(
            timer_section,
            text="ゲーム時間",
            font=("Arial", 12, "bold"),
            bg="#1a1a2e",
            fg="white",
        ).pack()

        # タイマー時間選択用のラジオボタン
        timer_buttons_frame = tk.Frame(timer_section, bg="#1a1a2e")
        timer_buttons_frame.pack(pady=(3, 0))

        self.duration_var = tk.StringVar(value=str(self.selected_duration))
        durations = ["30", "60", "180"]
        duration_labels = ["30秒", "60秒", "180秒"]

        for duration, label in zip(durations, duration_labels):
            rb = tk.Radiobutton(
                timer_buttons_frame,
                text=label,
                variable=self.duration_var,
                value=duration,
                font=("Arial", 10),
                bg="#1a1a2e",
                fg="white",
                selectcolor="#16213e",
                activebackground="#1a1a2e",
                activeforeground="white",
                command=self.on_duration_change,
                indicatoron=1,  # Ensure radio button indicator is visible
            )
            rb.pack(side="left", padx=10)

        # 推奨年齢選択エリア（初期状態では非表示）
        self.user_type_section = tk.Frame(settings_frame, bg="#1a1a2e")
        # 初期状態では pack しない（非表示）

        # 推奨年齢ラベル
        self.user_type_label = tk.Label(
            self.user_type_section,
            text="推奨年齢",
            font=("Arial", 12, "bold"),
            bg="#1a1a2e",
            fg="white",
        )
        self.user_type_label.pack()

        # ユーザータイプ選択用のラジオボタン
        self.user_type_buttons_frame = tk.Frame(self.user_type_section, bg="#1a1a2e")
        self.user_type_buttons_frame.pack(pady=(3, 0))

        self.user_type_var = tk.StringVar(value=self.selected_user_type)
        user_types = ["7歳", "12歳", "15歳", "18歳", "20歳以上"]

        self.user_type_radios = []
        for user_type in user_types:
            rb = tk.Radiobutton(
                self.user_type_buttons_frame,
                text=user_type,
                variable=self.user_type_var,
                value=user_type,
                font=("Arial", 10),
                bg="#1a1a2e",
                fg="white",
                selectcolor="#16213e",
                activebackground="#1a1a2e",
                activeforeground="white",
                command=self.on_user_type_change,
                indicatoron=1,  # Ensure radio button indicator is visible
            )
            rb.pack(side="left", padx=10)
            self.user_type_radios.append(rb)

        # ボタンエリア (最下部)
        button_frame = tk.Frame(self.root, bg="#1a1a2e", height=50)
        button_frame.pack(fill="x")
        button_frame.pack_propagate(False)

        buttons_container = tk.Frame(button_frame, bg="#1a1a2e")
        buttons_container.pack(expand=True)

        self.start_button = tk.Button(
            buttons_container,
            text="ゲーム開始",
            font=("Arial", 10, "bold"),
            bg="#4CAF50",
            fg="black",
            width=10,
            height=1,
            command=self.start_game,
            activebackground="#45a049",
            activeforeground="white",
            disabledforeground="white",
            relief="flat",
            bd=0,
        )
        self.start_button.pack(side="left", padx=5)

        self.reset_button = tk.Button(
            buttons_container,
            text="リセット",
            font=("Arial", 10, "bold"),
            bg="#f44336",
            fg="black",
            width=10,
            height=1,
            command=self.reset_game,
            activebackground="#da190b",
            activeforeground="white",
            disabledforeground="white",
            relief="flat",
            bd=0,
        )
        self.reset_button.pack(side="left", padx=5)

        # OpenAI利用可能かどうかで状態を決定
        generate_state = "normal" if self.openai_client else "disabled"
        generate_bg = "#2196F3" if self.openai_client else "#666666"

        self.generate_button = tk.Button(
            buttons_container,
            text="課題文生成",
            font=("Arial", 10, "bold"),
            bg=generate_bg,
            fg="black",
            width=10,
            height=1,
            command=self.generate_sentences,
            activebackground="#1976D2",
            activeforeground="white",
            disabledforeground="white",
            relief="flat",
            bd=0,
            state=generate_state,
        )
        self.generate_button.pack(side="left", padx=5)

        # キーボードイベントをrootにバインド
        self.root.bind("<KeyPress>", self.on_key_press)
        self.root.focus_set()
        self.update_displays()

    def on_user_type_change(self):
        """ユーザータイプ変更時のコールバック"""
        new_user_type = self.user_type_var.get()
        print(
            f"User type callback triggered: {self.selected_user_type} -> {new_user_type}"
        )
        self.selected_user_type = new_user_type
        print(f"User type changed to: {self.selected_user_type}")

    def on_duration_change(self):
        """タイマー時間変更時のコールバック"""
        new_duration = int(self.duration_var.get())
        print(
            f"Duration callback triggered: {self.selected_duration} -> {new_duration}"
        )
        self.selected_duration = new_duration
        self.game_duration = self.selected_duration
        print(f"Game duration changed to: {self.selected_duration} seconds")

    def generate_sentences(self):
        """課題文生成ボタンのコールバック"""
        if not self.openai_client:
            print("OpenAI client not available")
            return

        # 推奨年齢選択UI を表示
        self.show_user_type_selection()

    def show_user_type_selection(self):
        """推奨年齢選択UIを表示"""
        # 推奨年齢選択エリアを表示
        self.user_type_section.pack(pady=(15, 10))

        # 生成ボタン用のフレーム
        if not hasattr(self, "generate_buttons_frame"):
            self.generate_buttons_frame = tk.Frame(self.user_type_section, bg="#1a1a2e")
            self.generate_buttons_frame.pack(pady=(10, 0))

        # 生成開始ボタンを追加
        if not hasattr(self, "generate_start_button"):
            self.generate_start_button = tk.Button(
                self.generate_buttons_frame,
                text="生成開始",
                font=("Arial", 8, "bold"),
                bg="#4CAF50",
                fg="black",
                width=10,
                height=1,
                command=self.start_generation,
                activebackground="#45a049",
                activeforeground="white",
                relief="flat",
                bd=0,
            )
            self.generate_start_button.pack(side="left", padx=(0, 10))

        # キャンセルボタンを追加
        if not hasattr(self, "generate_cancel_button"):
            self.generate_cancel_button = tk.Button(
                self.generate_buttons_frame,
                text="キャンセル",
                font=("Arial", 8, "bold"),
                bg="#f44336",
                fg="black",
                width=10,
                height=1,
                command=self.hide_user_type_selection,
                activebackground="#da190b",
                activeforeground="white",
                relief="flat",
                bd=0,
            )
            self.generate_cancel_button.pack(side="left")

    def hide_user_type_selection(self):
        """推奨年齢選択UIを非表示"""
        self.user_type_section.pack_forget()

    def start_generation(self):
        """実際の生成処理を開始"""
        # 選択されたユーザータイプを更新
        self.selected_user_type = self.user_type_var.get()

        # UIを非表示
        self.hide_user_type_selection()

        # ボタンを無効化して処理中表示
        self.generate_button.config(text="生成中...", state="disabled")

        def do_generate():
            try:
                new_words = self.generate_sentences_with_openai()
                if new_words:
                    self.words = new_words
                    print(
                        f"Generated {len(new_words)} sentences for {self.selected_user_type}"
                    )
                    # 使用済み文章リストをクリア（新しい課題文セット）
                    self.used_sentences.clear()
                else:
                    print(f"Sentence generation failed for {self.selected_user_type}")
            except Exception as e:
                print(f"Error generating sentences: {e}")

            # ボタンを元に戻す
            self.generate_button.config(text="課題文生成", state="normal")

        # 非同期で実行
        self.root.after(100, do_generate)

    def start_game(self):
        if not self.game_active:
            # タイマーの背景色をリセット
            self.timer_label.config(
                bg="#1a1a2e", fg="#FFC107", relief="flat", bd=0, padx=0, pady=0
            )

            # 統計表示をクリア
            self.p1_stats_label.config(text="")
            self.p2_stats_label.config(text="")
            self.p1_words_typed = 0
            self.p1_correct_chars = 0
            self.p_total_chars = 0
            self.p2_words_typed = 0
            self.p2_correct_chars = 0
            self.p2_total_chars = 0

            self.start_button.config(state="disabled")
            self.countdown_value = 3
            self.start_countdown()

    def reset_game(self):
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None

        if self.countdown_job:
            self.root.after_cancel(self.countdown_job)
            self.countdown_job = None

        self.game_active = False
        self.countdown_value = 3  # カウントダウン値をリセット

        # 単語データもリセット
        self.current_word_data = None
        self.current_romaji = ""

        # Player 1 リセット
        self.p1_score = 0
        self.p1_words_typed = 0
        self.p1_current_position = 0
        self.p1_correct_chars = 0
        self.p1_total_chars = 0
        self.p1_perfect_typing = True
        self.p1_perfect_count = 0

        # Player 2 リセット
        self.p2_score = 0
        self.p2_words_typed = 0
        self.p2_current_position = 0
        self.p2_correct_chars = 0
        self.p2_total_chars = 0
        self.p2_perfect_typing = True
        self.p2_perfect_count = 0

        # 共通リセット
        self.start_time = 0

        # 使用済み文章リストをリセット
        self.used_sentences.clear()

        # ゲーム時間を60秒にリセット
        self.selected_duration = 60
        self.game_duration = 60
        self.duration_var.set("60")

        # 推奨年齢を12歳にリセット
        self.selected_user_type = "12歳"
        self.user_type_var.set("12歳")

        self.p1_score_label.config(text=f"スコア: {self.p1_score}")
        self.p2_score_label.config(text=f"スコア: {self.p2_score}")

        # 統計表示をクリア
        self.p1_stats_label.config(text="")
        self.p2_stats_label.config(text="")

        # 前回の統計キャッシュをクリア
        if hasattr(self, "_last_p1_stats"):
            delattr(self, "_last_p1_stats")
        if hasattr(self, "_last_p2_stats"):
            delattr(self, "_last_p2_stats")

        # タイマーを隠して背景をリセット
        self.timer_label.config(
            text="", bg="#1a1a2e", fg="#FFC107", relief="flat", bd=0, padx=0, pady=0
        )
        self.start_button.config(text="ゲーム開始", state="normal")
        self.hide_word()
        self.update_displays()

    def new_word(self):
        # 使用可能な文章（まだ使用されていない）を取得
        available_words = [
            word for word in self.words if word["japanese"] not in self.used_sentences
        ]

        # 使用可能な文章がない場合は、すべての文章をリセット
        if not available_words:
            self.used_sentences.clear()
            available_words = self.words.copy()
            print("All sentences used, resetting for new round")

        # 使用可能な文章から選択
        if available_words:
            self.current_word_data = random.choice(available_words)
            self.current_romaji = self.current_word_data["romaji"]

            # 使用済みリストに追加
            self.used_sentences.add(self.current_word_data["japanese"])

            self.p1_current_position = 0
            self.p2_current_position = 0

            # パーフェクトタイピングフラグをリセット
            self.p1_perfect_typing = True
            self.p2_perfect_typing = True

            self.update_word_display()
        else:
            # フォールバック: リストが空の場合
            print("No words available")

    def on_key_press(self, event):
        if not self.game_active:
            return

        # 特殊キーは無視
        if len(event.char) != 1 or not event.char.isprintable():
            return

        typed_char = event.char

        # Player 1 (小文字 + ハイフン) の入力処理
        if (
            typed_char.islower() or typed_char == "-"
        ) and self.p1_current_position < len(self.current_romaji):
            correct_char = self.current_romaji[self.p1_current_position].lower()
            # ハイフンの場合は小文字変換しない
            if typed_char == "-":
                correct_char = self.current_romaji[self.p1_current_position]

            self.p1_total_chars += 1

            if typed_char == correct_char:
                self.p1_correct_chars += 1
                self.p1_score += 10
                self.p1_current_position += 1

                # Player 1 単語完了チェック
                if self.p1_current_position >= len(self.current_romaji):
                    self.p1_words_typed += 1
                    self.p1_score += 50

                    # パーフェクトタイピングボーナス
                    if self.p1_perfect_typing:
                        self.p1_score += 100
                        self.p1_perfect_count += 1

                    self.new_word()  # どちらか完了で次の単語へ

                self.update_displays()
            else:
                # ミスタイプ：パーフェクトタイピングフラグをオフ
                self.p1_perfect_typing = False

        # Player 2 (大文字 + ハイフン) の入力処理
        elif (
            typed_char.isupper() or typed_char == "-"
        ) and self.p2_current_position < len(self.current_romaji):
            correct_char = self.current_romaji[self.p2_current_position].upper()
            # ハイフンの場合は大文字変換しない
            if typed_char == "-":
                correct_char = self.current_romaji[self.p2_current_position]

            self.p2_total_chars += 1

            if typed_char == correct_char:
                self.p2_correct_chars += 1
                self.p2_score += 10
                self.p2_current_position += 1

                # Player 2 単語完了チェック
                if self.p2_current_position >= len(self.current_romaji):
                    self.p2_words_typed += 1
                    self.p2_score += 50

                    # パーフェクトタイピングボーナス
                    if self.p2_perfect_typing:
                        self.p2_score += 100
                        self.p2_perfect_count += 1

                    self.new_word()  # どちらか完了で次の単語へ

                self.update_displays()
            else:
                # ミスタイプ：パーフェクトタイピングフラグをオフ
                self.p2_perfect_typing = False

    def update_displays(self):
        """全表示を更新"""
        self.p1_score_label.config(text=f"スコア: {self.p1_score}")
        self.p2_score_label.config(text=f"スコア: {self.p2_score}")
        self.update_stats()
        self.update_word_display()
        # タイマーは別のメソッドで更新されるため、ここでは呼ばない

    def start_countdown(self):
        """カウントダウン開始"""
        if self.countdown_value > 0:
            self.timer_label.config(text=str(self.countdown_value))
            self.countdown_value -= 1
            self.countdown_job = self.root.after(1000, self.start_countdown)
        else:
            # カウントダウン終了、ゲーム開始
            self.actual_start_game()

    def actual_start_game(self):
        """実際のゲーム開始処理"""
        self.game_active = True
        self.start_time = time.time()
        self.start_button.config(state="disabled")
        self.root.focus_set()

        # 新しいゲーム開始時に使用済み文章をクリア
        self.used_sentences.clear()

        # パーフェクトカウントをリセット
        self.p1_perfect_count = 0
        self.p2_perfect_count = 0

        # 新しいゲーム開始時は統計表示とキャッシュをクリア（start_game()で実行済み）

        self.new_word()
        # タイマー表示を開始
        self.timer_label.config(text=f"残り時間\n{self.game_duration}")
        # タイマーを開始
        self.update_timer()
        self.timer_job = self.root.after(self.game_duration * 1000, self.end_game)

    def update_timer(self):
        """タイマー更新"""
        if self.game_active:
            elapsed = time.time() - self.start_time
            remaining = max(0, self.game_duration - elapsed)
            timer_text = f"残り時間\n{remaining:.0f}"
            self.timer_label.config(text=timer_text)

            if remaining > 0:
                self.root.after(100, self.update_timer)

    def end_game(self):
        """ゲーム終了処理"""
        self.game_active = False
        self.start_button.config(text="ゲーム開始", state="normal")

        # 勝者決定と色設定
        if self.p1_score > self.p2_score:
            winner = "PLAYER 1 の勝ち！"
            winner_bg_color = "#4CAF50"  # Player 1の緑色
            winner_text_color = "white"
        elif self.p2_score > self.p1_score:
            winner = "PLAYER 2 の勝ち！"
            winner_bg_color = "#2196F3"  # Player 2の青色
            winner_text_color = "white"
        else:
            winner = "引き分け！"
            winner_bg_color = "#FFC107"  # 黄色
            winner_text_color = "black"

        # タイマー位置にゲーム結果を表示（色付き背景）
        result_text = f"ゲーム終了\n{winner}"
        self.timer_label.config(
            text=result_text,
            bg=winner_bg_color,
            fg=winner_text_color,
            relief="solid",
            bd=2,
            padx=20,
            pady=10,
        )

    def update_word_display(self):
        """現在の入力位置をハイライト表示"""
        if not self.current_word_data:
            return

        # 新しい単語の場合のみ、表示を再構築
        if (
            not hasattr(self, "current_displayed_word")
            or self.current_displayed_word != self.current_word_data["japanese"]
        ):
            self.create_word_display()
            self.current_displayed_word = self.current_word_data["japanese"]
        else:
            # 既存の表示の色のみを更新（ちらつき防止）
            self.update_character_colors()

    def create_word_display(self):
        """新しい単語の表示を作成"""
        # Player 1 の文字表示を再構築
        for label in self.p1_char_labels:
            label.destroy()
        self.p1_char_labels.clear()

        # 日本語表示
        japanese_label = tk.Label(
            self.p1_char_frame,
            text=self.current_word_data["japanese"],
            font=("Arial", 14, "bold"),
            bg="#16213e",
            fg="#eee",
        )
        japanese_label.pack(pady=(3, 8))
        self.p1_char_labels.append(japanese_label)

        # ローマ字表示（文字ごとにハイライト）
        self.p1_romaji_frame = tk.Frame(self.p1_char_frame, bg="#16213e")
        self.p1_romaji_frame.pack()
        self.p1_char_labels.append(self.p1_romaji_frame)

        self.p1_romaji_labels = []
        for i, char in enumerate(self.current_romaji):
            label = tk.Label(
                self.p1_romaji_frame,
                text=char.lower(),
                font=("Arial", 16, "bold"),
                bg="#16213e",
                fg="#eee",
                pady=0,
                padx=1,
            )
            label.pack(side="left")
            self.p1_char_labels.append(label)
            self.p1_romaji_labels.append(label)

        # Player 2 の文字表示を再構築
        for label in self.p2_char_labels:
            label.destroy()
        self.p2_char_labels.clear()

        # 日本語表示
        japanese_label2 = tk.Label(
            self.p2_char_frame,
            text=self.current_word_data["japanese"],
            font=("Arial", 14, "bold"),
            bg="#16213e",
            fg="#eee",
        )
        japanese_label2.pack(pady=(3, 8))
        self.p2_char_labels.append(japanese_label2)

        # ローマ字表示（文字ごとにハイライト）
        self.p2_romaji_frame = tk.Frame(self.p2_char_frame, bg="#16213e")
        self.p2_romaji_frame.pack()
        self.p2_char_labels.append(self.p2_romaji_frame)

        self.p2_romaji_labels = []
        for i, char in enumerate(self.current_romaji):
            label = tk.Label(
                self.p2_romaji_frame,
                text=char.lower(),
                font=("Arial", 16, "bold"),
                bg="#16213e",
                fg="#eee",
                pady=0,
                padx=1,
            )
            label.pack(side="left")
            self.p2_char_labels.append(label)
            self.p2_romaji_labels.append(label)

        # 初回色更新
        self.update_character_colors()

    def update_character_colors(self):
        """文字の色のみを更新（ちらつき防止）"""
        if not hasattr(self, "p1_romaji_labels") or not hasattr(
            self, "p2_romaji_labels"
        ):
            return

        # Player 1の色更新
        for i, label in enumerate(self.p1_romaji_labels):
            if i < self.p1_current_position:
                color = "#666666"  # ダークグレー（完了）
            elif i == self.p1_current_position:
                color = "#FFC107"  # 黄（現在位置）
            else:
                color = "#eee"  # 白（未入力）
            label.config(fg=color)

        # Player 2の色更新
        for i, label in enumerate(self.p2_romaji_labels):
            if i < self.p2_current_position:
                color = "#666666"  # ダークグレー（完了）
            elif i == self.p2_current_position:
                color = "#FFC107"  # 黄（現在位置）
            else:
                color = "#eee"  # 白（未入力）
            label.config(fg=color)

    def hide_word(self):
        """単語を非表示にする"""
        # Player 1 の文字表示をクリア
        for label in self.p1_char_labels:
            label.destroy()
        self.p1_char_labels.clear()

        # Player 2 の文字表示をクリア
        for label in self.p2_char_labels:
            label.destroy()
        self.p2_char_labels.clear()

        # 現在表示中の単語をクリア
        if hasattr(self, "current_displayed_word"):
            delattr(self, "current_displayed_word")

    def update_stats(self):
        """統計情報を更新"""
        if not self.game_active:
            return

        elapsed_time = time.time() - self.start_time
        if elapsed_time > 0:
            # Player 1 統計
            p1_cpm = (
                (self.p1_correct_chars / elapsed_time) * 60
                if self.p1_correct_chars > 0
                else 0
            )
            p1_accuracy = (
                (self.p1_correct_chars / self.p1_total_chars) * 100
                if self.p1_total_chars > 0
                else 0
            )

            # Player 2 統計
            p2_cpm = (
                (self.p2_correct_chars / elapsed_time) * 60
                if self.p2_correct_chars > 0
                else 0
            )
            p2_accuracy = (
                (self.p2_correct_chars / self.p2_total_chars) * 100
                if self.p2_total_chars > 0
                else 0
            )

            # 統計テキストの構築
            p1_text = f"CPM: {p1_cpm:.1f} | 正確度: {p1_accuracy:.1f}% | 単語: {self.p1_words_typed} | パーフェクト: {self.p1_perfect_count}"
            p2_text = f"CPM: {p2_cpm:.1f} | 正確度: {p2_accuracy:.1f}% | 単語: {self.p2_words_typed} | パーフェクト: {self.p2_perfect_count}"

            # 前回の値と比較して、変更がある場合のみ更新
            if not hasattr(self, "_last_p1_stats") or self._last_p1_stats != p1_text:
                self.p1_stats_label.config(text=p1_text)
                self._last_p1_stats = p1_text

            if not hasattr(self, "_last_p2_stats") or self._last_p2_stats != p2_text:
                self.p2_stats_label.config(text=p2_text)
                self._last_p2_stats = p2_text


if __name__ == "__main__":
    root = tk.Tk()
    game = VsTypingDojo(root)
    root.mainloop()
