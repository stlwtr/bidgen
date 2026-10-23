"""后台生成线程（fd 级捕获 pdf2docx 页进度与 [bidgen] 阶段进度）。"""

from __future__ import annotations

import os
import queue
import re
import threading

from PySide6.QtCore import QThread, Signal

from .. import cli


class _QueueWriter:
    def __init__(self, q: "queue.Queue[str]") -> None:
        self.q = q
        self._buf = ""

    def write(self, data: str) -> int:
        self._buf += data
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            if line.strip():
                self.q.put(line)
        return len(data)

    def flush(self) -> None:
        pass


class Worker(QThread):
    log = Signal(str)
    progress = Signal(int, int, str)  # value, maximum, label
    done = Signal(bool, str)

    def __init__(self, pdf: str, outdir: str, supplier_path: str, with_tender: bool):
        super().__init__()
        self.pdf = pdf
        self.outdir = outdir
        self.supplier_path = supplier_path
        self.with_tender = with_tender
        self.q: "queue.Queue[str]" = queue.Queue()

    def run(self) -> None:
        read_fd, write_fd = os.pipe()
        old_out, old_err = os.dup(1), os.dup(2)
        os.dup2(write_fd, 1)
        os.dup2(write_fd, 2)
        pump = threading.Thread(target=self._pump, args=(read_fd,), daemon=True)
        pump.start()
        try:
            if self.with_tender:
                self.log.emit("【1/2】转换招标文件为 Word…")
                tender = os.path.join(self.outdir, "招标文件.docx")
                cli._convert(self.pdf, tender, True)
                self.log.emit("已生成：" + tender)
            self.log.emit("【2/2】生成投标文件…")
            bid = os.path.join(self.outdir, "投标文件.docx")
            cli._generate(self.pdf, bid, self.supplier_path, True)
            self.log.emit("已生成：" + bid)
            self.done.emit(True, self.outdir)
        except Exception as exc:  # noqa: BLE001 - surface a readable message in the GUI
            self.q.put("错误：" + str(exc))
            self.done.emit(False, str(exc))
        finally:
            os.dup2(old_out, 1)
            os.dup2(old_err, 2)
            os.close(old_out)
            os.close(old_err)
            os.close(write_fd)

    def _pump(self, read_fd: int) -> None:
        with os.fdopen(read_fd, "r", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                line = raw.rstrip()
                if line:
                    self.q.put(line)

    def poll(self) -> None:
        try:
            while True:
                self._handle(self.q.get_nowait())
        except queue.Empty:
            pass

    _STAGE_RE = re.compile(r"\[bidgen\]\s*(\d+)/(\d+)\s*(.*)")
    _PAGE_RE = re.compile(r"\((\d+)/(\d+)\)\s*Page\s*(\d+)")

    def _handle(self, line: str) -> None:
        m = self._STAGE_RE.search(line)
        if m:
            n, total, stage = int(m.group(1)), int(m.group(2)), m.group(3).strip()
            self.progress.emit(n, total, f"生成投标文件：{stage}（{n}/{total}）")
            return
        m = self._PAGE_RE.search(line)
        if m:
            n, total = int(m.group(1)), int(m.group(2))
            self.progress.emit(n, total, f"转换招标文件：{n}/{total} 页")
            return
        self.log.emit(line)
