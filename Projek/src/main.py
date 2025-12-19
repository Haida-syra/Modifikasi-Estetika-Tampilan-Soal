import os
import ctypes 

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try: ctypes.windll.user32.SetProcessDPIAware()
    except: pass

import tkinter as tk
from tkinter import ttk, messagebox
import random
import datetime
import uuid 

from utils import (
    ensure_dirs, load_questions_for_package, normalize_correct_answer,
    pick_questions_with_fresh_priority, pick_daily_challenge_by_level,
    load_json, save_json, HISTORY_FILE, list_packages_from_soal
)

# ================= CONFIG =================
ensure_dirs()

QUESTIONS_PER_LEVEL = 8
SESSION_SECONDS = 75 * 60
DAILY_NUM = 5
DAILY_POINTS = {"easy": 1, "medium": 2, "hard": 3}

# ================= APP =================
class QuizApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Latihan Soal UTBK")
        try:
            self.state("normalized")
        except Exception:
            pass

        self._style()

        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self.history = load_json(HISTORY_FILE, [])
        self.packages = list_packages_from_soal()

        # state
        self.questions = []
        self.idx = 0
        self.score = 0
        self.daily_score = 0
        self.daily_breakdown = {"easy": 0, "medium": 0, "hard": 0}
        self.is_daily = False
        self.showing_explanation = False

        self.timer_label = None
        self.remaining = SESSION_SECONDS
        self.timer_job = None

        self.current_package = None
        self.current_level = None

        self._home()
    def _style(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("Choice.TRadiobutton", background="white", foreground="#8B4C39", font=("Segoe UI", 11), padding=10)
        s.configure("TButton", font=("Baskerville", 12))

    def clear(self):
        for widget in self.container.winfo_children():
            widget.destroy()

        self.after_cancel(self.start_canvas_confetti)
    # ================= BAGIAN ANIMASI =================
    def start_canvas_confetti(self):
        flowers = ["🌸", "🌷", "✨", "🎀", "🌹"]
        for _ in range(20): 
            x = random.randint(0, 1000)
            y = random.randint(-200, -50)
            f_text = random.choice(flowers)
            
           
            flower_id = self.content_canvas.create_text(x, y, text=f_text, font=("Arial", 18), fill="#FFB6C1")
            
            self.animate_canvas_flower(flower_id, random.randint(2, 5))

    def animate_canvas_flower(self, item_id, speed):
        try:
            self.content_canvas.move(item_id, 0, speed)
            pos = self.content_canvas.coords(item_id)
            
            if pos[1] < 800: 
                self.after(30, lambda: self.animate_canvas_flower(item_id, speed))
            else:
                self.content_canvas.delete(item_id)
        except:
            pass

    # ================= STYLE =================
    def _style(self):
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except Exception:
            pass

        bg = "#f9e7f4"
        text = "#4a044e"
        btn = "#f9bfe9"
        hover = "#fe5cb5"

        s.configure("TFrame", background=bg)
        s.configure("TLabel", background=bg, foreground=text)
        s.configure("Title.TLabel", font=("Segoe UI", 28, "bold"))
        s.configure("Subtitle.TLabel", font=("Segoe UI", 14))

        s.configure(
            "TButton",
            font=("Segoe UI", 16),
            padding=12,
            background=btn,
            foreground=text
        )
        s.map("TButton", background=[("active", hover)])

        s.configure(
            "Choice.TRadiobutton",
            background=bg,
            foreground=text,
            font=("Segoe UI", 16),
            padding=8
        )
        s.map("Choice.TRadiobutton", background=[("active", hover)])

    # ================= UTILS =================
    def clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    # ================= TIMER =================
    def start_timer(self):
       
        if self.timer_job:
            try:
                self.after_cancel(self.timer_job)
            except Exception:
                pass
            self.timer_job = None

        self.remaining = SESSION_SECONDS
        self.timer_job = self.after(1000, self._tick)

    def _tick(self):
        try:
            m, s = divmod(self.remaining, 60)
            if self.timer_label and getattr(self.timer_label, "winfo_exists", lambda: False)():
                try:
                    self.timer_label.config(text=f"⏱ {m:02d}:{s:02d}")
                except tk.TclError:
                    pass
        except Exception:
            pass

        if self.remaining <= 0:
            if self.timer_job:
                try:
                    self.after_cancel(self.timer_job)
                except Exception:
                    pass
                self.timer_job = None
            try:
                messagebox.showinfo("Waktu Habis", "Sesi selesai")
            except Exception:
                pass
            self.finish()
            return

        self.remaining -= 1
        try:
            self.timer_job = self.after(1000, self._tick)
        except Exception:
            self.timer_job = None

    # ================= HOME =================
    def _home(self):
        self.clear()
        
        main_layout = tk.Frame(self.container, bg="#FFF0F5")
        main_layout.pack(fill="both", expand=True)

        sidebar = tk.Frame(main_layout, bg="white", width=260, highlightbackground="#FFB6C1", highlightthickness=1)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="🎀", font=("Arial", 45), bg="white").pack(pady=(30, 0))
        tk.Label(sidebar, text="Bloom Study", font=("Georgia", 18, "italic"), fg="#8B4C39", bg="white").pack(pady=(0, 30))

        menu_items = [
            ("🏠  Home", self._home),
            ("✨  Daily Challenge", self._daily_menu),
            ("📜  History", self._history),
            ("❌  Exit", self.quit)
        ]

        for txt, cmd in menu_items:
            btn = tk.Button(sidebar, text=txt, font=("Baskerville", 12), fg="#8B4C39", bg="white", 
                            relief="flat", activebackground="#FFF0F5", cursor="hand2", anchor="w", 
                            padx=25, pady=12, command=cmd)
            btn.pack(fill="x")

        self.content_canvas = tk.Canvas(main_layout, bg="#FFF0F5", highlightthickness=0)
        self.content_canvas.pack(side="right", fill="both", expand=True)

        ui_frame = tk.Frame(self.content_canvas, bg="#FFF0F5")
        self.content_canvas.create_window((10, 10), window=ui_frame, anchor="nw") 

        def center_ui(event):
            canvas_w = event.width
            canvas_h = event.height
            self.content_canvas.coords(ui_id, canvas_w/2, canvas_h/2)

        ui_id = self.content_canvas.create_window(0, 0, window=ui_frame, anchor="center")
        self.content_canvas.bind("<Configure>", center_ui)

       
        hero = tk.Frame(ui_frame, bg="white", padx=40, pady=40, highlightbackground="#FFB6C1", highlightthickness=2)
        hero.pack(pady=(0, 30))
        
        tk.Label(hero, text="✧ Your Future Starts Today ✧", font=("Georgia", 24, "italic"), fg="#8B4C39", bg="white").pack()
        tk.Label(hero, text="“Believe in your bloom, success is just one study away.”", font=("Baskerville", 11), fg="#DB7093", bg="white").pack(pady=(10, 0))

        
        start_btn = tk.Button(ui_frame, text="✦ Start New Session ✦", font=("Georgia", 14, "bold"), 
                              bg="#FFB6C1", fg="white", relief="flat", padx=35, pady=15, 
                              command=self._package_menu, cursor="hand2")
        start_btn.pack()


        self.after(500, self.start_canvas_confetti)
    # ================= FITUR SCROLL SOAL =================
    def _show_question(self):
        self.clear()
        if self.idx >= len(self.questions):
            self.finish()
            return

        q = self.questions[self.idx]

      
        bottom_bar = tk.Frame(self.container, bg="#FFF0F5", height=80)
        bottom_bar.pack(side="bottom", fill="x", pady=10)
        bottom_bar.pack_propagate(False) 

        scroll_container = tk.Frame(self.container, bg="#FFF0F5")
        scroll_container.pack(side="top", fill="both", expand=True)

        canvas = tk.Canvas(scroll_container, bg="#FFF0F5", highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=canvas.yview)
        
        
        self.scrollable_frame = tk.Frame(canvas, bg="#FFF0F5")
        
     
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

       
        canvas_window = canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
      
        def on_canvas_configure(e):
            canvas.itemconfig(canvas_window, width=e.width)

        canvas.bind("<Configure>", on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

       
        quiz_content = tk.Frame(self.scrollable_frame, bg="white", padx=40, pady=30,
                                highlightbackground="#FFB6C1", highlightthickness=1)
        quiz_content.pack(pady=20, padx=100, fill="x")

        question_text = q.get("question", "")
        tk.Label(quiz_content, text=f"Soal {self.idx + 1}", font=("Arial", 9, "bold"), 
                 bg="white", fg="#DB7093").pack(anchor="w")
        
        tk.Label(quiz_content, text=question_text, font=("Georgia", 11), 
                 bg="white", fg="#8B4C39", wraplength=700, justify="left").pack(anchor="w", pady=15)

     
        self.var_ans = tk.IntVar(value=-1)
        for i, choice in enumerate(q.get("choices", [])):
            rb = tk.Radiobutton(quiz_content, text=choice, variable=self.var_ans, value=i,
                                font=("Segoe UI", 10), bg="white", fg="#8B4C39",
                                activebackground="white", wraplength=600, justify="left")
            rb.pack(anchor="w", pady=5)

        # --- TOMBOL NAVIGASI (DI BOTTOM BAR) ---
        tk.Button(bottom_bar, text="🏠 Menu", font=("Arial", 10), bg="white",
                  command=self._home, padx=20, pady=5).pack(side="left", padx=50)

        tk.Button(bottom_bar, text="Next Step ▷", font=("Arial", 10, "bold"), 
                  bg="#FFB6C1", fg="white", command=self._next, padx=30, pady=5).pack(side="right", padx=50)
    # ================= PACKAGE =================
    def _package_menu(self):
        self.clear()
        
       
        main_frame = tk.Frame(self.container, bg="#FFF0F5")
        main_frame.pack(fill="both", expand=True, padx=40, pady=40)

        tk.Button(main_frame, text="← Back", font=("Baskerville", 10), fg="#8B4C39", bg="#FFF0F5", 
                  relief="flat", command=self._home, cursor="hand2").pack(anchor="w")

        tk.Label(main_frame, text="✧ Select Your Subject ✧", font=("Georgia", 24, "italic"), 
                 fg="#8B4C39", bg="#FFF0F5").pack(pady=(10, 30))

        grid_container = tk.Frame(main_frame, bg="#FFF0F5")
        grid_container.pack(fill="both", expand=True)

       
        cols = 3
        for i, pkg in enumerate(self.packages):
            r, c = divmod(i, cols)
            
            pkg_card = tk.Frame(grid_container, bg="white", padx=20, pady=20, 
                                highlightbackground="#FFB6C1", highlightthickness=1)
            pkg_card.grid(row=r, column=c, padx=15, pady=15, sticky="nsew")
            
        
            tk.Label(pkg_card, text="📖", font=("Segoe UI Symbol", 30), bg="white").pack()
            tk.Label(pkg_card, text=pkg.upper(), font=("Georgia", 16, "bold"), 
                     fg="#DB7093", bg="white").pack(pady=5)
            
           
            btn = tk.Button(pkg_card, text="Pilih Paket", font=("Baskerville", 11), 
                            bg="#FFB6C1", fg="white", relief="flat", padx=15, 
                            command=lambda p=pkg: self._level_menu(p))
            btn.pack(pady=10)


        for j in range(cols):
            grid_container.grid_columnconfigure(j, weight=1)

    def _level_menu(self, package):
        self.clear()
        box = ttk.Frame(self.container)
        box.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(box, text=f"Paket {package}", style="Title.TLabel").pack(pady=20)
        for lvl in ("easy", "medium", "hard"):
            ttk.Button(box, text=lvl.capitalize(), width=30,
                       command=lambda l=lvl: self.start_quiz(package, l)).pack(pady=6)

        ttk.Button(box, text="⬅ Kembali", command=self._package_menu).pack(pady=20)

    # ================= START QUIZ =================
    def start_quiz(self, package, level):
        pkg = (package or "").strip()
        lvl = (level or "").strip().lower()
        self.current_package = pkg
        self.current_level = lvl

        raw = load_questions_for_package(pkg)
        if not raw:
            messagebox.showinfo("Info", f"Soal tidak tersedia untuk paket: {package}")
            print(f"[DEBUG] start_quiz: package={pkg!r} raw_count=0")
            return

        db = normalize_correct_answer(raw) or []
        print(f"[DEBUG] start_quiz package={pkg!r} raw_count={len(raw)} normalized={len(db)} level={lvl}")

        self.questions = pick_questions_with_fresh_priority(
            db, QUESTIONS_PER_LEVEL, self.history, pkg, lvl
        ) or []

        print(f"[DEBUG] start_quiz: selected_count={len(self.questions)} (QUESTIONS_PER_LEVEL={QUESTIONS_PER_LEVEL})")

        if not self.questions:
            messagebox.showinfo("Info", f"Soal tidak tersedia untuk paket {package} pada level {level}")
            return

        self.idx = 0
        self.score = 0
        self.is_daily = False
        self.start_timer()
        self.show_question()

    # ================= DAILY =================
    def _daily_menu(self):
        self.clear()
        box = ttk.Frame(self.container)
        box.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(box, text="Daily Challenge", style="Title.TLabel").pack(pady=20)
        if not self.packages:
            ttk.Label(box, text="Tidak ada paket tersedia", style="Subtitle.TLabel").pack(pady=10)
        for p in self.packages:
            ttk.Button(box, text=p, width=30,
                       command=lambda x=p: self.start_daily(x)).pack(pady=6)

        ttk.Button(box, text="⬅ Kembali", command=self._home).pack(pady=20)

    def start_daily(self, package):
        """
        Daily challenge is a mix of levels with different point weights.
        Default distribution: hard=1, medium=2, easy=2 (total DAILY_NUM=5).
        If not enough questions in a level, fill from other levels.
        """
        pkg = (package or "").strip()
        self.current_package = pkg
        self.current_level = None

        raw = load_questions_for_package(pkg)
        if not raw:
            messagebox.showinfo("Info", f"Soal tidak tersedia untuk paket: {package}")
            print(f"[DEBUG] start_daily: package={pkg!r} raw_count=0")
            return

        db = normalize_correct_answer(raw) or []

        desired = {"hard": 1, "medium": 2, "easy": 2}
        selected = []

        for lvl, cnt in desired.items():
            if cnt <= 0:
                continue
            part = pick_daily_challenge_by_level(db, pkg, level=lvl, count=cnt)
            if part:
                selected.extend(part)

        if len(selected) < DAILY_NUM:
            selected_ids = {q.get("id") for q in selected if q.get("id")}
            remaining_pool = [q for q in db if (q.get("question") or q.get("choices") or q.get("reading")) and q.get("id") not in selected_ids]
            if remaining_pool:
                random.shuffle(remaining_pool)
                need = DAILY_NUM - len(selected)
                selected.extend(remaining_pool[:need])

        if len(selected) < DAILY_NUM:
            extra = pick_daily_challenge_by_level(db, pkg, level='all', count=DAILY_NUM - len(selected))
            if extra:
                selected.extend(extra)

        if not selected:
            messagebox.showinfo("Info", "Soal daily tidak tersedia")
            print(f"[DEBUG] start_daily: package={pkg!r} selected_count=0 after fallback")
            return

        if len(selected) > DAILY_NUM:
            selected = selected[:DAILY_NUM]

        self.questions = selected
        print(f"[DEBUG] start_daily package={pkg!r} total_db={len(db)} selected={len(self.questions)}")

        self.idx = 0
        self.daily_score = 0
        self.daily_breakdown = {"easy": 0, "medium": 0, "hard": 0}
        self.is_daily = True
        self.start_timer()
        self.show_question()

    # ================= QUESTION =================
    def show_question(self):
            self.showing_explanation = False
            self.clear()
            
            
            self.radio = [] 

            if not self.questions:
                messagebox.showinfo("Info", "Tidak ada soal")
                self._home()
                return


            main_bg = tk.Frame(self.container, bg="#FDF2F8")
            main_bg.pack(fill="both", expand=True)

            flowers = [
                (0.05, 0.1, "🌸"), (0.95, 0.1, "🌺"),
                (0.05, 0.9, "🌷"), (0.95, 0.9, "🌸")
            ]
            for relx, rely, icon in flowers:
                tk.Label(main_bg, text=icon, font=("Arial", 40), bg="#FDF2F8", fg="#FBCFE8").place(relx=relx, rely=rely, anchor="center")

            tk.Label(main_bg, text="Bloom Study", font=("Georgia", 24, "italic"), bg="#FDF2F8", fg="#8B4C39").pack(pady=(20, 0))

            card_border = tk.Frame(main_bg, bg="#F9A8D4", padx=2, pady=2)
            card_border.place(relx=0.5, rely=0.48, anchor="center")

            card = tk.Frame(card_border, bg="white", padx=50, pady=40)
            card.pack()

            q = self.questions[self.idx]

            header_frame = tk.Frame(card, bg="white")
            header_frame.pack(fill="x")
            
            tk.Label(header_frame, text=f"✧ Soal {self.idx+1} / {len(self.questions)} ✧", 
                    font=("Georgia", 11), bg="white", fg="#DB7093").pack(side="left")
            
            self.timer_label = tk.Label(header_frame, font=("Segoe UI", 11, "bold"), bg="white", fg="#8B4C39")
            self.timer_label.pack(side="right")

            tk.Frame(card, height=1, width=100, bg="#FCE7F3").pack(pady=10)

            tk.Label(card, text=q.get("question", "-"), font=("Georgia", 15), 
                    bg="white", fg="#4A044E", wraplength=600, justify="center").pack(pady=20)

            self.answer_var = tk.IntVar(value=-1)
            
            for i, c in enumerate(q.get("choices", [])):
                f = tk.Frame(card, bg="white")
                f.pack(anchor="w", pady=5, padx=50)
                
                rb = ttk.Radiobutton(f, text=c, variable=self.answer_var, value=i, 
                                    style="Choice.TRadiobutton")
                rb.pack(side="left")
                
                self.radio.append(rb) 

            self.feedback = tk.Label(card, font=("Segoe UI", 12, "bold"), bg="white")
            self.feedback.pack(pady=5)
            self.expl = tk.Label(card, font=("Segoe UI", 10), bg="white", wraplength=550, fg="#8B4C39")
            self.expl.pack()

            
            btn_container = tk.Frame(main_bg, bg="#FDF2F8")
            btn_container.pack(side="bottom", pady=40)

            tk.Button(btn_container, text="🌸 Next Step", font=("Georgia", 12, "bold"), 
                    bg="#F472B6", fg="white", relief="flat", padx=40, pady=10,
                    command=self.next_step, cursor="hand2").pack(pady=5)

            tk.Button(btn_container, text="⬅ Kembali", font=("Georgia", 11), 
                    bg="#FBCFE8", fg="#8B4C39", relief="flat", padx=35, pady=8,
                    command=self._home, cursor="hand2").pack(pady=5)
        # ================= NEXT =================
    def next_step(self):
        if not self.questions:
            return

        q = self.questions[self.idx]

        if not self.showing_explanation:
            sel = self.answer_var.get()
            if sel == -1:
                messagebox.showwarning("Pilih", "Pilih jawaban dulu")
                return

            for rb in self.radio:
                rb.state(["disabled"])

            if sel == q.get("correct_answer"):
                if self.is_daily:
                    lvl = (q.get("level") or "easy").strip().lower()
                    pts = DAILY_POINTS.get(lvl, 1)
                    self.daily_score += pts
                    if lvl not in self.daily_breakdown:
                        self.daily_breakdown[lvl] = 0
                    self.daily_breakdown[lvl] += pts
                else:
                    self.score += 1
                self.feedback.config(text="✅ BENAR")
            else:
                self.feedback.config(text="❌ SALAH")

            self.expl.config(text=f"Pembahasan:\n{q.get('explanation','-')}")
            self.showing_explanation = True
            return

        if self.idx < len(self.questions) - 1:
            self.idx += 1
            self.show_question()
        else:
            self.finish()

    # ================= FINISH =================
    def finish(self):
        self.clear()
        
        # 1. Simpan Data ke History
        new_record = {
            "id": str(uuid.uuid4())[:8],
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "package": self.current_package,
            "score": self.score
            }
        self.history.append(new_record)
        save_json(HISTORY_FILE, self.history)

        # 2. Jalankan Animasi Perayaan
        self.after(300, self.start_canvas_confetti)

        # 3. Tampilkan Kartu Hasil di Tengah
        result_card = tk.Frame(self.container, bg="white", padx=50, pady=50, 
                               highlightbackground="#FFB6C1", highlightthickness=2)
        result_card.place(relx=0.5, rely=0.45, anchor="center")

        tk.Label(result_card, text="🌸 Quiz Completed! 🌸", font=("Georgia", 18, "italic"), 
                 bg="white", fg="#8B4C39").pack(pady=(0, 10))
        
        tk.Label(result_card, text=f"Your Score: {self.score}", font=("Georgia", 36, "bold"), 
                 bg="white", fg="#DB7093").pack(pady=20)

        tk.Button(result_card, text="Back to Home", font=("Georgia", 11), bg="#FFB6C1", 
                  fg="white", relief="flat", padx=20, pady=10, command=self._home).pack()

    # ================= HALAMAN RIWAYAT (HISTORY) =================
    def _history(self):
        self.clear()
        

        history_frame = tk.Frame(self.container, bg="#FFF0F5", padx=40, pady=30)
        history_frame.pack(fill="both", expand=True)

        tk.Label(history_frame, text="📜 Study History", font=("Georgia", 22, "italic"), 
                 fg="#8B4C39", bg="#FFF0F5").pack(pady=(0, 20))

        header = tk.Frame(history_frame, bg="#FFB6C1")
        header.pack(fill="x")
        
        cols = [("Date & Time", 0.3), ("Subject", 0.3), ("Score", 0.2), ("Status", 0.2)]
        for txt, width in cols:
            tk.Label(header, text=txt, font=("Arial", 10, "bold"), bg="#FFB6C1", 
                     fg="white", pady=8).pack(side="left", expand=True, fill="x")


        data_container = tk.Frame(history_frame, bg="white", highlightbackground="#FFB6C1", highlightthickness=1)
        data_container.pack(fill="both", expand=True, pady=10)

        if not self.history:
            tk.Label(data_container, text="Belum ada riwayat pengerjaan soal. ✨", 
                     font=("Arial", 10), bg="white", fg="#DB7093").pack(pady=50)
        else:
            for record in reversed(self.history[-10:]):
                row = tk.Frame(data_container, bg="white")
                row.pack(fill="x", pady=1)
                tgl = record.get('date', '-')
                sub = record.get('package', 'UTBK')
                skr = record.get('score', 0)

                tk.Label(row, text=tgl, bg="white", font=("Arial", 9)).pack(side="left", expand=True, fill="x")
                tk.Label(row, text=sub, bg="white", font=("Arial", 9)).pack(side="left", expand=True, fill="x")
                tk.Label(row, text=skr, bg="white", font=("Arial", 9, "bold"), fg="#DB7093").pack(side="left", expand=True, fill="x")
                tk.Label(row, text="Completed ✅", bg="white", font=("Arial", 8), fg="#4CAF50").pack(side="left", expand=True, fill="x")

        btn_frame = tk.Frame(history_frame, bg="#FFF0F5")
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="◁ Back", font=("Arial", 10), bg="white", relief="flat", 
                  padx=20, command=self._home, cursor="hand2").pack(side="left", padx=10)
        
        tk.Button(btn_frame, text="🗑 Clear History", font=("Arial", 10), bg="#FF69B4", fg="white", 
                  relief="flat", padx=20, command=self.clear_history_data, cursor="hand2").pack(side="left", padx=10)
    def clear_history_data(self):
        if messagebox.askyesno("Confirm", "Hapus semua riwayat belajar kamu? ✨"):
            self.history = [] 
            save_json(HISTORY_FILE, self.history) 
            self._history() 
            messagebox.showinfo("Success", "Riwayat berhasil dibersihkan! 🌸")

# ================= MENJALANKAN APLIKASI =================
if __name__ == "__main__":
    try:
        app = QuizApp()
        app.mainloop()
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(error_msg)
        messagebox.showerror("Aplikasi Error", f"Terjadi kesalahan saat menjalankan aplikasi:\n{e}")