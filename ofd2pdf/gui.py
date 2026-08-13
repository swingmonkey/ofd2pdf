"""Tkinter GUI for OFD-to-PDF conversion.

Run directly with ``python -m ofd2pdf.gui``, or package into a standalone
Windows executable with the PyInstaller spec in the repository root
(see README "打包为 Windows EXE").
"""

from __future__ import annotations

import os
import queue
import sys
import threading
import traceback
from pathlib import Path

# Under PyInstaller ``--windowed`` builds ``sys.stdout``/``sys.stderr`` are
# ``None``; any ``print``/``logging`` call would then raise. Redirect to a
# null sink early so third-party loggers (loguru, logging) stay harmless.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from ofd2pdf import __version__
from ofd2pdf.converter import convert_file, list_backends


class Ofd2PdfApp:
    """Small single-window GUI around the ofd2pdf converter."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title(f"OFD 转 PDF 工具  v{__version__}")
        root.geometry("760x560")
        root.minsize(640, 480)

        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.backend_var = tk.StringVar(value="easyofd")
        self.backend_choices: dict[str, str] = {}

        self._log_queue: "queue.Queue[tuple[str, str]]" = queue.Queue()
        self._worker: threading.Thread | None = None

        self._build_ui()
        self._refresh_backends()
        root.after(120, self._poll_queue)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 6}

        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill="both", expand=True)

        # Input row
        row1 = ttk.Frame(frame)
        row1.pack(fill="x", **pad)
        ttk.Label(row1, text="输入 OFD：", width=12).pack(side="left")
        ttk.Entry(row1, textvariable=self.input_var).pack(side="left", fill="x", expand=True)
        ttk.Button(row1, text="选择文件…", command=self._pick_input_file).pack(side="left", padx=(6, 2))
        ttk.Button(row1, text="选择目录…", command=self._pick_input_dir).pack(side="left", padx=2)

        # Output row
        row2 = ttk.Frame(frame)
        row2.pack(fill="x", **pad)
        ttk.Label(row2, text="输出位置：", width=12).pack(side="left")
        ttk.Entry(row2, textvariable=self.output_var).pack(side="left", fill="x", expand=True)
        ttk.Button(row2, text="浏览…", command=self._pick_output).pack(side="left", padx=(6, 0))

        # Backend row
        row3 = ttk.Frame(frame)
        row3.pack(fill="x", **pad)
        ttk.Label(row3, text="转换后端：", width=12).pack(side="left")
        self.backend_combo = ttk.Combobox(
            row3, textvariable=self.backend_var, state="readonly", width=24
        )
        self.backend_combo.pack(side="left")
        self.backend_hint = ttk.Label(row3, text="", foreground="#666666")
        self.backend_hint.pack(side="left", padx=8)

        # Action row
        row4 = ttk.Frame(frame)
        row4.pack(fill="x", **pad)
        self.convert_btn = ttk.Button(row4, text="开始转换", command=self._on_convert)
        self.convert_btn.pack(side="left")
        ttk.Button(row4, text="打开输出位置", command=self._open_output).pack(side="left", padx=8)
        ttk.Button(row4, text="清空日志", command=self._clear_log).pack(side="left")

        # Log area
        log_frame = ttk.LabelFrame(frame, text="转换日志", padding=6)
        log_frame.pack(fill="both", expand=True, **pad)
        self.log = scrolledtext.ScrolledText(log_frame, height=14, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True)

    def _pick_input_file(self) -> None:
        path = filedialog.askopenfilename(
            title="选择 OFD 文件",
            filetypes=[("OFD 文档", "*.ofd"), ("所有文件", "*.*")],
        )
        if path:
            self.input_var.set(path)
            if not self.output_var.get():
                self.output_var.set(str(Path(path).with_suffix(".pdf")))

    def _pick_input_dir(self) -> None:
        path = filedialog.askdirectory(title="选择包含 OFD 文件的目录")
        if path:
            self.input_var.set(path)

    def _pick_output(self) -> None:
        if Path(self.input_var.get()).is_dir():
            path = filedialog.askdirectory(title="选择输出目录")
        else:
            path = filedialog.asksaveasfilename(
                title="选择输出 PDF",
                defaultextension=".pdf",
                filetypes=[("PDF 文件", "*.pdf")],
            )
        if path:
            self.output_var.set(path)

    def _refresh_backends(self) -> None:
        info = list_backends()
        available = [name for name, d in info.items() if d["available"]]
        self.backend_choices = {d["name"]: d["description"] for d in info.values()}
        self.backend_combo["values"] = list(info.keys())
        if self.backend_var.get() not in info:
            self.backend_var.set("easyofd")
        if available and self.backend_var.get() not in available:
            self.backend_var.set(available[0])
        hint_parts = []
        for name, d in info.items():
            mark = "v" if d["available"] else "x"
            hint_parts.append(f"{name}{mark}")
        self.backend_hint["text"] = "  ".join(hint_parts) + "  (v 可用)"

    # ----------------------------------------------------------- actions
    def _on_convert(self) -> None:
        if self._worker and self._worker.is_alive():
            return

        src = self.input_var.get().strip()
        dst = self.output_var.get().strip()
        backend = self.backend_var.get()

        if not src:
            messagebox.showwarning("提示", "请先选择输入 OFD 文件或目录。")
            return
        if not dst:
            messagebox.showwarning("提示", "请选择输出位置。")
            return

        src_path = Path(src)
        if not src_path.exists():
            messagebox.showerror("错误", f"输入路径不存在：\n{src}")
            return

        self.convert_btn.config(state="disabled")
        self._append_log(f"== 开始转换（后端：{backend}） ==")
        self._worker = threading.Thread(
            target=self._convert_worker, args=(src_path, Path(dst), backend), daemon=True
        )
        self._worker.start()

    def _convert_worker(self, src: Path, dst: Path, backend: str) -> None:
        try:
            if src.is_dir():
                self._convert_dir(src, dst, backend)
            else:
                self._convert_one(src, dst, backend)
            self._log_queue.put(("ok", "转换完成。"))
        except Exception as exc:  # noqa: BLE001 - surface everything to the user
            self._log_queue.put(("error", f"转换失败：{exc}"))
            self._log_queue.put(("detail", traceback.format_exc()))

    def _convert_dir(self, src: Path, dst: Path, backend: str) -> None:
        dst.mkdir(parents=True, exist_ok=True)
        files = sorted(src.glob("*.ofd"))
        if not files:
            self._log_queue.put(("warn", f"目录 {src} 下没有找到 *.ofd 文件。"))
            return
        self._log_queue.put(("info", f"发现 {len(files)} 个 OFD 文件。"))
        ok = 0
        for idx, f in enumerate(files, 1):
            out = dst / f.with_suffix(".pdf").name
            self._log_queue.put(("info", f"[{idx}/{len(files)}] {f.name} -> {out.name}"))
            try:
                convert_file(f, out, backend=backend)
                ok += 1
                self._log_queue.put(("ok", f"  done {f.name}"))
            except Exception as exc:  # noqa: BLE001
                self._log_queue.put(("error", f"  fail {f.name}: {exc}"))
        self._log_queue.put(("info", f"批量完成：成功 {ok}/{len(files)}。"))

    def _convert_one(self, src: Path, dst: Path, backend: str) -> None:
        self._log_queue.put(("info", f"{src.name} -> {dst.name}"))
        convert_file(src, dst, backend=backend)
        self._log_queue.put(("ok", f"已输出：{dst.resolve()}"))

    # ------------------------------------------------------------ logging
    def _append_log(self, text: str, tag: str = "info") -> None:
        self.log.config(state="normal")
        self.log.insert("end", text + "\n", tag)
        self.log.see("end")
        self.log.config(state="disabled")

    def _poll_queue(self) -> None:
        try:
            while True:
                tag, text = self._log_queue.get_nowait()
                self._append_log(text, tag)
        except queue.Empty:
            pass

        if self._worker is not None and not self._worker.is_alive():
            self.convert_btn.config(state="normal")
            self._worker = None

        self.root.after(120, self._poll_queue)

    def _clear_log(self) -> None:
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")

    def _open_output(self) -> None:
        path = self.output_var.get().strip()
        if not path:
            messagebox.showinfo("提示", "还没有选择输出位置。")
            return
        p = Path(path)
        target = p if p.is_dir() else p.parent
        if not target.exists():
            messagebox.showinfo("提示", f"输出位置尚不存在：\n{target}")
            return
        os.startfile(str(target))  # type: ignore[attr-defined]


def main() -> int:
    # Headless mode: when command-line arguments are present, delegate to the
    # console CLI so the same EXE can be scripted (e.g. batch jobs). With no
    # arguments it launches the GUI.
    if len(sys.argv) > 1:
        from ofd2pdf.cli import main as cli_main

        return cli_main(sys.argv[1:])

    root = tk.Tk()
    app = Ofd2PdfApp(root)

    app.log.tag_configure("ok", foreground="#1a7f37")
    app.log.tag_configure("error", foreground="#c62828")
    app.log.tag_configure("warn", foreground="#b26a00")
    app.log.tag_configure("info", foreground="#333333")
    app.log.tag_configure("detail", foreground="#999999")

    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
