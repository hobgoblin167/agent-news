import queue
import re
import subprocess
import threading
import time
import traceback
import tkinter as tk
from tkinter import font as tkfont
from pathlib import Path

import requests

from database import init_db
from graph import graph


MODEL_PATH = r"C:\Users\madsu\Desktop\LLM_models\Qwen3.5-9B-Q4_K_M.gguf"
LLAMA_COMMAND = [
    "llama-server", "-m", MODEL_PATH, "-c", "4096", "-ngl", "25",
    "-np", "1", "--reasoning", "off", "--port", "8080",
]
HEALTH_URL = "http://127.0.0.1:8080/health"


class NewsAgentGUI:
    def __init__(self, root):
        self.root = root
        self.llama_process = None
        self.events = queue.Queue()
        self.closed = threading.Event()
        self.process_lock = threading.Lock()
        self.busy = False
        self.bold_text = False
        self.pending_star = ""
        self.root.title("Новости")
        self.root.geometry("940x720")
        self.root.minsize(480, 360)
        self.root.configure(bg="white")
        icon_path = Path(__file__).resolve().parent / "assets" / "news-agent.ico"
        if icon_path.exists():
            self.root.iconbitmap(str(icon_path))
        self.create_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.poll_id = self.root.after(30, self.drain_events)

    def create_ui(self):
        # One control, centered until the first run; the rest is the answer.
        self.action = tk.Canvas(
            self.root, width=152, height=152, bg="white",
            highlightthickness=0, bd=0, takefocus=True, cursor="hand2",
        )
        self.action.place(relx=0.5, rely=0.5, anchor="center")
        self.action.create_oval(9, 13, 143, 147, fill="#eeedf6", outline="")
        self.button_shape = self.action.create_oval(
            7, 5, 145, 143, fill="#6354cf", outline="",
        )
        self.button_icon = self.action.create_text(
            76, 47, text="▶", fill="white", font=("Segoe UI", 20),
        )
        self.button_text = self.action.create_text(
            76, 91, text="Собрать\nновости", fill="white",
            font=("Segoe UI", 11, "bold"), justify="center", width=116,
        )
        self.action.bind("<Button-1>", self.press_button)
        self.action.bind("<ButtonRelease-1>", self.release_button)
        self.action.bind("<Return>", lambda event: self.run_agent())
        self.action.bind("<space>", lambda event: self.run_agent())
        self.action.bind("<Enter>", lambda event: self.hover(True))
        self.action.bind("<Leave>", lambda event: self.hover(False))
        self.action.bind("<FocusIn>", lambda event: self.hover(True))
        self.action.bind("<FocusOut>", lambda event: self.hover(False))
        # Keep explicit named fonts alive, including the real bold face on Windows.
        self.body_font = tkfont.Font(root=self.root, family="Segoe UI", size=13, weight="normal")
        self.bold_font = tkfont.Font(root=self.root, family="Segoe UI", size=14, weight="bold")
        self.output = tk.Text(
            self.root, bg="white", fg="#29292e", relief="flat", bd=0,
            highlightthickness=0, font=self.body_font, wrap="word",
            padx=12, pady=12, spacing1=3, spacing3=7,
            selectbackground="#e2e5ef", selectforeground="#202026",
            state="disabled", cursor="arrow",
        )
        self.output.tag_configure("bold", font=self.bold_font, foreground="#111116")
        self.output.tag_configure("structure", font=self.bold_font, foreground="#111116")
        self.output.tag_raise("bold")

    def inside_button(self, event):
        return (event.x - 76) ** 2 + (event.y - 74) ** 2 <= 69 ** 2

    def press_button(self, event):
        self.button_pressed = not self.busy and self.inside_button(event)
        if self.button_pressed:
            self.action.focus_set()
            self.action.itemconfigure(self.button_shape, fill="#493aa9")

    def release_button(self, event):
        pressed = getattr(self, "button_pressed", False)
        self.button_pressed = False
        self.hover(self.inside_button(event))
        if pressed and self.inside_button(event):
            self.run_agent()

    def hover(self, active):
        if not self.busy:
            self.action.itemconfigure(
                self.button_shape, fill="#7565df" if active else "#6354cf"
            )

    def set_button(self, text):
        self.action.itemconfigure(self.button_text, text=text.replace(" ", "\n", 1))
        self.action.itemconfigure(self.button_icon, text="⋯" if self.busy else "▶")
        self.action.itemconfigure(
            self.button_shape, fill="#9990cc" if self.busy else "#6354cf"
        )
        self.action.configure(cursor="arrow" if self.busy else "hand2")

    def append_text(self, text, final=False):
        follow = self.output.yview()[1] >= 0.99
        first_line = int(self.output.index("end-1c").split(".")[0])
        self.output.configure(state="normal")
        # Hold a trailing star: the second half of ** may arrive next token.
        text = self.pending_star + text
        self.pending_star = ""
        if not final and text.endswith("*") and not text.endswith("**"):
            text = text[:-1]
            self.pending_star = "*"
        parts = text.split("**")
        for index, part in enumerate(parts):
            if index:
                self.bold_text = not self.bold_text
            if part:
                self.output.insert(tk.END, part, ("bold",) if self.bold_text else ())
        self.format_structure(first_line)
        self.output.configure(state="disabled")
        if follow:
            self.output.see(tk.END)

    def format_structure(self, first_line):
        # The model may follow the digest template without Markdown markers.
        # Recheck the unfinished line as tokens arrive; do not bold its body text.
        self.output.tag_remove("structure", f"{first_line}.0", "end")
        last_line = int(self.output.index("end-1c").split(".")[0])
        for number in range(first_line, last_line + 1):
            line = self.output.get(f"{number}.0", f"{number}.end")
            stripped = line.strip()
            if stripped.rstrip(":").upper() in {"ГЛАВНОЕ", "ДЕТАЛИ", "МЕНЕЕ ВАЖНОЕ"}:
                self.output.tag_add("structure", f"{number}.0", f"{number}.end")
            elif re.match(r"^\s*\d+[.)]\s+\S", line):
                self.output.tag_add("structure", f"{number}.0", f"{number}.end")
            else:
                label = re.match(r"^\s*(?:[-•]\s+)?(?:Коротко|Почему это важно)\s*:", line, re.IGNORECASE)
                if label:
                    self.output.tag_add("structure", f"{number}.0", f"{number}.{label.end()}")

    def drain_events(self):
        # Only the main thread touches Tk. Batch tokens to keep the UI responsive.
        for _ in range(400):
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "text":
                self.append_text(value)
            elif kind == "status":
                self.set_button(value)
            elif kind == "done":
                self.append_text("", final=True)
                self.busy = False
                self.set_button(value)
        self.poll_id = self.root.after(30, self.drain_events)

    def stream_token(self, token):
        if not self.closed.is_set():
            self.events.put(("text", token))

    def ensure_server(self):
        self.events.put(("status", "Запускаю модель…"))
        deadline = time.monotonic() + 300
        while not self.closed.is_set():
            try:
                with requests.get(HEALTH_URL, timeout=2) as response:
                    if response.status_code == 200:
                        return True
                    if response.status_code != 503:
                        response.raise_for_status()
            except requests.ConnectionError:
                with self.process_lock:
                    if self.closed.is_set():
                        return False
                    if self.llama_process is None:
                        print("Starting llama-server...", flush=True)
                        # Inherit the terminal: server logs never enter the GUI.
                        self.llama_process = subprocess.Popen(LLAMA_COMMAND)
            except requests.Timeout:
                pass
            with self.process_lock:
                if self.llama_process is not None and self.llama_process.poll() is not None:
                    code = self.llama_process.returncode
                    self.llama_process = None
                    raise RuntimeError(f"llama-server exited with code {code}")
            if time.monotonic() >= deadline:
                raise TimeoutError("llama-server did not become ready within 300 seconds")
            self.closed.wait(0.5)
        return False

    def run_agent(self):
        if self.busy or self.closed.is_set():
            return
        self.busy = True
        self.action.place(relx=0.5, rely=0, y=16, anchor="n")
        self.output.place(relx=0.06, y=186, relwidth=0.88, relheight=1, height=-210)
        self.bold_text = False
        self.pending_star = ""
        self.output.configure(state="normal")
        self.output.delete("1.0", tk.END)
        self.output.configure(state="disabled")
        self.set_button("Запускаю модель…")
        threading.Thread(target=self.run_worker, daemon=True).start()

    def run_worker(self):
        label = "Обновить новости"
        try:
            if not self.ensure_server() or self.closed.is_set():
                return
            init_db()
            self.events.put(("status", "Собираю новости…"))
            result = graph.invoke({"stream_callback": self.stream_token})
            if not result.get("digest"):
                self.stream_token("Новых новостей пока нет.")
            print("News agent finished.", flush=True)
        except Exception:
            traceback.print_exc()
            # A retry label is enough; technical details stay in the terminal.
            label = "Повторить попытку"
        finally:
            self.events.put(("done", label))

    def close(self):
        self.closed.set()
        self.root.after_cancel(self.poll_id)
        self.root.destroy()
        threading.Thread(target=self.stop_owned_server, daemon=False).start()

    def stop_owned_server(self):
        with self.process_lock:
            process = self.llama_process
            self.llama_process = None
        if process is not None and process.poll() is None:
            print("Stopping llama-server...", flush=True)
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("LocalNewsAgent.Desktop")
    root = tk.Tk()
    app = NewsAgentGUI(root)
    root.mainloop()
