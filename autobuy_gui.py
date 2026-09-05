import queue
import threading
import datetime
import configparser
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

from e7core import E7Core, log_crash, app_path, SKYSTONES_PER_REFRESH


class Controls:
    def __init__(self):
        self._stop = threading.Event()
        self._resume = threading.Event()
        self._resume.set()

    def pause(self):
        self._resume.clear()

    def resume(self):
        self._resume.set()

    def stop(self):
        self._stop.set()
        self._resume.set()

    def is_paused(self):
        return not self._resume.is_set()

    def should_stop(self):
        return self._stop.is_set()

    def wait_if_paused(self):
        self._resume.wait()
        return not self._stop.is_set()


class RunState:
    def __init__(self):
        self.status = "Detectando emulador..."
        self.current_refresh = 0
        self.total_refresh = 0
        self.skystones_spent = 0
        self.skystones_total = 0
        self.bookmarks = 0
        self.medals = 0
        self.finished = False
        self.error = None
        self.stopped = False
        self.log = queue.Queue()

    def emit(self, msg):
        stamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log.put(f"[{stamp}] {msg}")


def worker(core, controls, state, rolls, delay):
    try:
        state.emit("Detectando emulador e display do E7...")
        core.setup()
        core.delay = delay
        state.emit(f"Device: {core.device}  |  display logico: {core.e7_input_display}"
                   f"  |  delay: {delay}x")
        res = core.screen()
        if not core.is_16_9(res):
            state.error = (f"Resolucao {res.size[0]}x{res.size[1]} nao suportada. "
                           "Use 16:9 (ex: 1920x1080).")
            state.finished = True
            return
        core.compute_coords(res)
        state.emit(f"Resolucao {res.size[0]}x{res.size[1]}. Iniciando "
                   f"{rolls} refreshes ({rolls * SKYSTONES_PER_REFRESH} skystones).")

        state.status = "Rodando"
        start = datetime.datetime.now()
        completed = 0
        for x in range(rolls + 1):
            if not controls.wait_if_paused():
                state.stopped = True
                state.emit("Encerrado pelo usuario.")
                break
            if core.is_disconnected():
                state.emit("Disconnect/rede instavel detectado. Pausando - "
                           "reconecte no jogo e clique Retomar.")
                state.status = "Pausado (disconnect)"
                controls.pause()
                if not controls.wait_if_paused():
                    state.stopped = True
                    state.emit("Encerrado pelo usuario.")
                    break
                state.status = "Rodando"
                continue
            bm, mm = core.scan_and_buy()
            state.bookmarks += bm
            state.medals += mm
            state.current_refresh = x
            state.skystones_spent = x * SKYSTONES_PER_REFRESH
            completed = x
            msg = f"Refresh {x}/{rolls}"
            if bm or mm:
                achados = []
                if bm:
                    achados.append(f"{bm}x Covenant Bookmark")
                if mm:
                    achados.append(f"{mm}x Mystic Medal")
                msg += "  -> COMPROU " + ", ".join(achados)
            state.emit(msg)
            if x == rolls:
                break
            if controls.should_stop():
                state.stopped = True
                state.emit("Encerrado pelo usuario.")
                break
            core.reroll()

        end = datetime.datetime.now()
        gold = ((184 * state.bookmarks) + (280 * state.medals)) * 1000
        state.emit(f"Fim. Bookmarks={5 * state.bookmarks}  Medals={50 * state.medals}  "
                   f"Gold={gold}")
        try:
            with open(app_path("logs.txt"), "a") as log:
                log.write(
                    f"Started at {start}\nEnded at {end}\n"
                    f"Time elapsed: {end - start}\nRefreshes = {completed}\n"
                    f"Skystones spent = {completed * SKYSTONES_PER_REFRESH}\n"
                    f"Covenant Bookmark = {5 * state.bookmarks}\n"
                    f"Mystic Medals = {50 * state.medals}\nGold Spent = {gold}\n\n")
        except Exception:
            pass
    except Exception:
        log_crash("\nErro na interface grafica")
        state.error = "Erro durante a execucao (veja crash.log)."
        state.emit("ERRO: veja crash.log")
    finally:
        state.finished = True


class App:
    def __init__(self, root):
        self.root = root
        self.core = None
        self.controls = None
        self.state = None
        self.thread = None

        root.title("E7 Shop refresher - Barbedo")
        root.resizable(False, False)
        root.configure(padx=16, pady=14)

        style = ttk.Style()
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass
        style.configure("Big.TButton", padding=(10, 6))
        style.configure("Val.TLabel", font=("Segoe UI", 10, "bold"))
        style.configure("Title.TLabel", font=("Segoe UI", 13, "bold"))

        ttk.Label(root, text="E7 Shop refresher - Barbedo", style="Title.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        inp = ttk.Frame(root)
        inp.grid(row=1, column=0, columnspan=3, sticky="we")

        ttk.Label(inp, text="Skystones a gastar:").grid(row=0, column=0, sticky="w",
                                                         pady=2)
        self.sky_var = tk.StringVar(value="")
        self.sky_entry = ttk.Entry(inp, width=10, textvariable=self.sky_var,
                                   justify="right")
        self.sky_entry.grid(row=0, column=1, sticky="w", padx=(6, 8), pady=2)
        self.sky_entry.focus()
        self.refresh_hint = ttk.Label(inp, text="cada refresh custa 3 skystones",
                                      foreground="#777")
        self.refresh_hint.grid(row=0, column=2, sticky="w")
        self.sky_var.trace_add("write", lambda *_: self._update_hint())

        ttk.Label(inp, text="Delay (velocidade):").grid(row=1, column=0, sticky="w",
                                                        pady=2)
        self.delay_var = tk.StringVar(value=self._config_delay())
        self.delay_entry = ttk.Entry(inp, width=10, textvariable=self.delay_var,
                                     justify="right")
        self.delay_entry.grid(row=1, column=1, sticky="w", padx=(6, 8), pady=2)
        self.delay_hint = ttk.Label(inp, text="menor = mais rapido (padrao 1.5)",
                                    foreground="#777")
        self.delay_hint.grid(row=1, column=2, sticky="w")
        self.delay_var.trace_add("write", lambda *_: self._update_delay_hint())

        btns = ttk.Frame(root)
        btns.grid(row=2, column=0, columnspan=3, sticky="we", pady=(12, 12))
        self.btn_start = ttk.Button(btns, text="Iniciar", style="Big.TButton",
                                    command=self.on_start)
        self.btn_pause = ttk.Button(btns, text="Pausar", style="Big.TButton",
                                    command=self.on_pause, state="disabled")
        self.btn_stop = ttk.Button(btns, text="Encerrar", style="Big.TButton",
                                   command=self.on_stop, state="disabled")
        self.btn_start.grid(row=0, column=0, padx=(0, 6))
        self.btn_pause.grid(row=0, column=1, padx=6)
        self.btn_stop.grid(row=0, column=2, padx=(6, 0))

        ttk.Separator(root, orient="horizontal").grid(
            row=3, column=0, columnspan=3, sticky="we", pady=(0, 10))

        grid = ttk.Frame(root)
        grid.grid(row=4, column=0, columnspan=3, sticky="we")
        self.val = {}
        rows = [
            ("status", "Status:"),
            ("refresh", "Refresh:"),
            ("sky", "Skystones:"),
            ("bm", "Covenant Bookmarks:"),
            ("mm", "Mystic Medals:"),
        ]
        for i, (key, label) in enumerate(rows):
            ttk.Label(grid, text=label).grid(row=i, column=0, sticky="w", pady=2)
            v = ttk.Label(grid, text="-", style="Val.TLabel")
            v.grid(row=i, column=1, sticky="w", padx=(12, 0), pady=2)
            self.val[key] = v
        self.val["status"].config(text="Pronto")

        ttk.Label(root, text="Log:").grid(row=5, column=0, sticky="w", pady=(12, 2))
        self.log_box = scrolledtext.ScrolledText(
            root, width=52, height=10, state="disabled", wrap="word",
            font=("Consolas", 9))
        self.log_box.grid(row=6, column=0, columnspan=3, sticky="we")

        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _config_delay(self):
        try:
            cfg = configparser.ConfigParser()
            cfg.read(app_path("config.ini"))
            return cfg.get("Refresh", "delay").strip()
        except Exception:
            return "1.5"

    def _parse_delay(self):
        try:
            d = float(self.delay_var.get().strip().replace(",", "."))
        except (ValueError, TypeError):
            return None
        return d if d > 0 else None

    def _update_delay_hint(self):
        d = self._parse_delay()
        if d is None:
            self.delay_hint.config(text="valor invalido", foreground="#c00000")
        elif d < 0.8:
            self.delay_hint.config(text=f"{d}x - rapido (cuidado com erros)",
                                   foreground="#b06000")
        else:
            self.delay_hint.config(text=f"{d}x - menor = mais rapido",
                                   foreground="#0a7d00")

    def _parse_rolls(self):
        try:
            sky = int(float(self.sky_var.get()))
        except (ValueError, TypeError):
            return None, None
        rolls = sky // SKYSTONES_PER_REFRESH
        return rolls, rolls * SKYSTONES_PER_REFRESH

    def _update_hint(self):
        raw = self.sky_var.get().strip()
        if not raw:
            self.refresh_hint.config(text="cada refresh custa 3 skystones",
                                     foreground="#777")
            return
        rolls, real_sky = self._parse_rolls()
        if rolls and rolls > 0:
            self.refresh_hint.config(
                text=f"= {rolls} refreshes  ({real_sky} skystones)",
                foreground="#0a7d00")
        else:
            self.refresh_hint.config(text="valor invalido", foreground="#c00000")

    def _append_log(self, text):
        self.log_box.config(state="normal")
        self.log_box.insert("end", text + "\n")
        if int(self.log_box.index("end-1c").split(".")[0]) > 1000:
            self.log_box.delete("1.0", "500.0")
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def _drain_log(self):
        while self.state and not self.state.log.empty():
            try:
                self._append_log(self.state.log.get_nowait())
            except queue.Empty:
                break

    def _set_running_ui(self, running):
        self.sky_entry.config(state="disabled" if running else "normal")
        self.delay_entry.config(state="disabled" if running else "normal")
        self.btn_start.config(state="disabled" if running else "normal")
        self.btn_pause.config(state="normal" if running else "disabled",
                              text="Pausar")
        self.btn_stop.config(state="normal" if running else "disabled")

    def on_start(self):
        rolls, real_sky = self._parse_rolls()
        if not rolls or rolls < 1:
            messagebox.showerror("Valor invalido",
                                 "Informe pelo menos 3 skystones (1 refresh).")
            return
        delay = self._parse_delay()
        if delay is None:
            messagebox.showerror("Delay invalido",
                                 "Informe um delay maior que 0 (ex: 1.5).")
            return

        self.core = E7Core()
        self.controls = Controls()
        self.state = RunState()
        self.state.total_refresh = rolls
        self.state.skystones_total = real_sky

        self._set_running_ui(True)
        self.thread = threading.Thread(
            target=worker, args=(self.core, self.controls, self.state, rolls, delay),
            daemon=True)
        self.thread.start()
        self.root.after(200, self._poll)

    def on_pause(self):
        if not self.controls:
            return
        if self.controls.is_paused():
            self.controls.resume()
            self.btn_pause.config(text="Pausar")
        else:
            self.controls.pause()
            self.btn_pause.config(text="Retomar")

    def on_stop(self):
        if self.controls:
            self.controls.stop()
            self.btn_stop.config(state="disabled")
            self.btn_pause.config(state="disabled")

    def on_close(self):
        if self.controls and self.thread and self.thread.is_alive():
            self.controls.stop()
        self.root.destroy()

    def _derive_status(self, s):
        if s.error:
            return "Erro"
        if s.finished:
            return "Encerrado" if s.stopped else "Concluido"
        if self.controls.should_stop():
            return "Encerrando (terminando refresh)..."
        if self.controls.is_paused():
            return "Pausado"
        return s.status

    def _poll(self):
        s = self.state
        self._drain_log()
        self.val["status"].config(text=self._derive_status(s))
        self.val["refresh"].config(text=f"{s.current_refresh} / {s.total_refresh}")
        self.val["sky"].config(text=f"{s.skystones_spent} / {s.skystones_total}")
        self.val["bm"].config(text=str(s.bookmarks))
        self.val["mm"].config(text=str(s.medals))

        if s.finished:
            self._drain_log()
            self._on_finished(s)
        else:
            self.root.after(300, self._poll)

    def _on_finished(self, s):
        self._set_running_ui(False)
        if s.error:
            messagebox.showerror("Erro", s.error)
            return
        gold = ((184 * s.bookmarks) + (280 * s.medals)) * 1000
        messagebox.showinfo(
            "Resultado",
            f"Covenant Bookmarks: {5 * s.bookmarks}\n"
            f"Mystic Medals: {50 * s.medals}\n"
            f"Gold gasto: {gold}\n"
            f"Refreshes feitos: {s.current_refresh}\n"
            f"Skystones gastos: {s.skystones_spent}")


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
