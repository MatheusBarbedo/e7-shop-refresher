import os
import sys
import subprocess
import re
import time
import random
import datetime
import logging
import configparser
from io import BytesIO

import pytesseract as ocr
from PIL import Image

SKYSTONES_PER_REFRESH = 3

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def app_path(name):
    return os.path.join(app_dir(), name)


def log_crash(handled=""):
    logging.basicConfig(filename=app_path("crash.log"))
    logging.exception(f"\n{datetime.datetime.now()}{handled}\n")


DISCONNECT_KEYWORDS = (
    "reconnect",
    "network error",
    "network status",
    "network is unstable",
    "server is unstable",
    "connection to the server",
    "has been lost",
    "disconnected",
)


class E7Core:
    def __init__(self):
        self.adb_path = None
        self.delay = 1.5
        self.delay_spread = 0.5
        self.device = None
        self.e7_display = None
        self.e7_input_display = None

    def _wait(self, mult):
        lo = max(0.0, self.delay - self.delay_spread)
        d = random.uniform(lo, self.delay)
        time.sleep(mult * d)

    def load_config(self, path="config.ini"):
        base = app_dir()
        adb = os.path.join(base, "platform-tools", "adb.exe")
        tess = os.path.join(base, "tesseract", "tesseract.exe")
        delay = 1.5

        cfg = configparser.ConfigParser()
        cfg_file = os.path.join(base, path)
        if os.path.exists(cfg_file):
            try:
                cfg.read(cfg_file)
                delay = cfg.getfloat("Refresh", "delay")
            except Exception:
                pass
        if not os.path.exists(adb):
            try:
                adb = cfg.get("Refresh", "adbPath")
            except Exception:
                pass
        if not os.path.exists(tess):
            try:
                tess = cfg.get("Refresh", "tesseractPath")
            except Exception:
                pass

        self.adb_path = '"' + adb + '"'
        ocr.pytesseract.tesseract_cmd = tess
        self.delay = delay

    def _adb_prefix(self):
        if self.device:
            return f"{self.adb_path} -s {self.device}"
        return self.adb_path

    def _run(self, args):
        p = subprocess.run(f"{self._adb_prefix()} {args}", shell=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           creationflags=_NO_WINDOW)
        return p.stdout, p.stdout.decode("utf-8", "ignore")

    COMMON_PORTS = [7555, 16384, 5555, 5556, 5554, 62001, 62025, 21503]

    def ensure_connected(self):
        for port in self.COMMON_PORTS:
            self._run(f"connect 127.0.0.1:{port}")

    def pick_device(self):
        _, txt = self._run("devices")
        serials = []
        for line in txt.splitlines()[1:]:
            line = line.strip()
            if line and "\t" in line and line.endswith("device"):
                serials.append(line.split("\t")[0])
        self.device = serials[0] if serials else None
        return self.device

    def _input_prefix(self):
        d = ""
        if self.e7_input_display is not None:
            d = f" -d {self.e7_input_display}"
        return f"{self._adb_prefix()} shell input{d}"

    def click(self, x, y):
        subprocess.run(f"{self._input_prefix()} tap {x} {y}", shell=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=_NO_WINDOW)

    def swipe(self, x1, y1, x2, y2):
        subprocess.run(f"{self._input_prefix()} swipe {x1} {y1} {x2} {y2}",
                       shell=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, creationflags=_NO_WINDOW)

    def screencap_bytes(self, display_id=None):
        d = f" -d {display_id}" if display_id else ""
        raw, _ = self._run(f"exec-out screencap -p{d}")
        i = raw.find(b"\x89PNG")
        if i > 0:
            raw = raw[i:]
        return raw

    def screen(self):
        return Image.open(BytesIO(self.screencap_bytes(self.e7_display)))

    def is_disconnected(self, img=None):
        try:
            if img is None:
                img = self.screen()
            text = ocr.image_to_string(img).lower()
        except Exception:
            return False
        return any(k in text for k in DISCONNECT_KEYWORDS)

    @staticmethod
    def _try_open(raw):
        try:
            return Image.open(BytesIO(raw))
        except Exception:
            return None

    @staticmethod
    def _is_mostly_black(img):
        small = img.convert("L").resize((64, 36))
        data = small.tobytes()
        return (sum(data) / len(data)) < 8

    def list_displays(self):
        _, txt = self._run("shell dumpsys display")
        pairs, seen = [], set()
        for m in re.finditer(r"displayId=(\d+),\s*uniqueId='local:(\d+)'", txt):
            lid = int(m.group(1))
            pid = m.group(2)
            if lid not in seen:
                seen.add(lid)
                pairs.append((lid, pid))
        return pairs

    def detect_e7_display(self):
        disp = self.list_displays()
        if len(disp) <= 1:
            self.e7_display = None
            self.e7_input_display = None
            return None, None
        for lid, pid in disp:
            if lid == 0:
                continue
            img = self._try_open(self.screencap_bytes(pid))
            if img and not self._is_mostly_black(img):
                self.e7_display, self.e7_input_display = pid, lid
                return pid, lid
        for lid, pid in disp:
            if lid != 0:
                self.e7_display, self.e7_input_display = pid, lid
                return pid, lid
        self.e7_display = self.e7_input_display = None
        return None, None

    def setup(self):
        self.load_config()
        self.ensure_connected()
        if not self.pick_device():
            raise RuntimeError(
                "Nenhum device conectado no ADB. Verifique se o emulador "
                "(MuMu) esta aberto com o Epic Seven.")
        self.detect_e7_display()

    def compute_coords(self, resolution):
        r = resolution.size[0] / 1280
        self.ratio = r
        self.rbx, self.rby = int(230 * r), int(660 * r)
        self.rbcx, self.rbcy = int(740 * r), int(440 * r)
        self.slotb = int(1150 * r)
        self.slot0, self.slot1, self.slot2 = int(160 * r), int(300 * r), int(450 * r)
        self.slot3, self.slot4, self.slot5 = int(595 * r), int(530 * r), int(670 * r)
        self.slotcx, self.slotcy = int(750 * r), int(510 * r)
        self.cropulx = int(680 * r)
        self.cropul0, self.cropul1, self.cropul2 = int(90 * r), int(232 * r), int(375 * r)
        self.cropul3, self.cropul4, self.cropul5 = int(525 * r), int(460 * r), int(605 * r)
        self.cropbrx = int(1000 * r)
        self.cropbr0, self.cropbr1, self.cropbr2 = int(180 * r), int(332 * r), int(475 * r)
        self.cropbr3, self.cropbr4, self.cropbr5 = int(625 * r), int(550 * r), int(695 * r)
        self.swipex = int(1000 * r)
        self.swipey1, self.swipey2 = int(575 * r), int(250 * r)

    @staticmethod
    def is_16_9(resolution):
        return (resolution.size[0] / 16) == (resolution.size[1] / 9)

    def reroll(self):
        self._wait(1)
        self.click(self.rbx, self.rby)
        self._wait(1)
        self.click(self.rbx, self.rby)
        self._wait(1)
        self.click(self.rbcx, self.rbcy)
        self._wait(1)
        self.click(self.rbcx, self.rbcy)
        self._wait(2)

    def buy(self, slot):
        self._wait(1)
        if slot == 5:
            y = self.slot5
        elif slot == 4:
            y = self.slot4
        else:
            self.swipe(self.swipex, self.swipey2, self.swipex, self.swipey1)
            self._wait(2)
            y = {3: self.slot3, 2: self.slot2, 1: self.slot1, 0: self.slot0}[slot]
        self._wait(2)
        self.click(self.slotb, y)
        self._wait(1)
        self.click(self.slotb, y)
        self._wait(1)
        self.click(self.slotcx, self.slotcy)
        self._wait(1)
        self.click(self.slotcx, self.slotcy)
        self._wait(2)
        self.swipe(self.swipex, self.swipey1, self.swipex, self.swipey2)
        self._wait(4)

    def scan_and_buy(self):
        images = []
        ss = self.screen()
        images.append(ss.crop((self.cropulx, self.cropul0, self.cropbrx, self.cropbr0)))
        images.append(ss.crop((self.cropulx, self.cropul1, self.cropbrx, self.cropbr1)))
        images.append(ss.crop((self.cropulx, self.cropul2, self.cropbrx, self.cropbr2)))
        images.append(ss.crop((self.cropulx, self.cropul3, self.cropbrx, self.cropbr3)))

        self._wait(1)
        self.swipe(self.swipex, self.swipey1, self.swipex, self.swipey2)
        self._wait(2)
        ss = self.screen()
        images.append(ss.crop((self.cropulx, self.cropul4, self.cropbrx, self.cropbr4)))
        images.append(ss.crop((self.cropulx, self.cropul5, self.cropbrx, self.cropbr5)))

        bookmarks = medals = 0
        slots = []
        for count, im in enumerate(images):
            text = ocr.image_to_string(im)
            if "Covenant Bookmarks" in text:
                slots.append(count)
                bookmarks += 1
            elif "Mystic Medals" in text:
                slots.append(count)
                medals += 1

        for slot in slots:
            self.buy(slot)

        return bookmarks, medals
