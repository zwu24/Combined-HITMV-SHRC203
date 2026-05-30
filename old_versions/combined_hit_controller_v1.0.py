"""Unified Tkinter controller for SIGMA KOKI HIT-MV and SHRC-203 HIT mode.

The vendor examples are intentionally small demo scripts.  This module keeps
the serial protocol details testable and puts the blocking serial work on a
worker thread so the Tkinter UI stays responsive.
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Iterable

try:
    import serial
    from serial.tools import list_ports
except Exception:  # pragma: no cover - allows tests to run without pyserial
    serial = None
    list_ports = None

import tkinter as tk
from tkinter import messagebox, ttk


DEFAULT_SLOW = "2000"
DEFAULT_FAST = "20000"
DEFAULT_RATE = "200"


class ControllerError(Exception):
    """Raised for serial or controller-command failures."""


def now_stamp() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def validate_integer_text(value: str, *, signed: bool = False) -> str:
    text = value.strip()
    if signed:
        if text in {"", "+", "-"} or not text.lstrip("+-").isdigit():
            raise ValueError(f"Expected a signed integer, got {value!r}")
    elif not text.isdigit():
        raise ValueError(f"Expected a positive integer, got {value!r}")
    return text


def split_reply(reply: str, width: int | None = None) -> list[str]:
    parts = reply.strip().split(",") if reply is not None else []
    if width is not None:
        if len(parts) < width:
            parts.extend([""] * (width - len(parts)))
        return parts[:width]
    return parts


@dataclass
class AxisState:
    controller_key: str
    controller_label: str
    axis: int
    display_name: str
    active: bool = False
    selected: bool = False
    position: str = ""
    ready: str = ""
    detail_status: str = ""
    slow: str = DEFAULT_SLOW
    fast: str = DEFAULT_FAST
    rate: str = DEFAULT_RATE


class SerialConnection:
    """Thin pyserial wrapper with CRLF command framing."""

    def __init__(
        self,
        label: str,
        logger: Callable[[str], None],
        terminator: str = "\r\n",
        is_cancelled: Callable[[], bool] | None = None,
    ) -> None:
        self.label = label
        self.logger = logger
        self.terminator = terminator
        self.is_cancelled = is_cancelled or (lambda: False)
        self._serial = None
        self._lock = threading.Lock()

    @property
    def is_open(self) -> bool:
        return bool(self._serial and self._serial.is_open)

    def connect(
        self,
        port: str,
        baudrate: int,
        timeout: float,
        rtscts: bool,
        bytesize: int = 8,
        parity: str = "N",
        stopbits: int = 1,
    ) -> None:
        if serial is None:
            raise ControllerError("pyserial is not installed. Install it with: pip install pyserial")
        if self.is_open:
            self.disconnect()
        try:
            self._serial = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=bytesize,
                parity=parity,
                stopbits=stopbits,
                timeout=timeout,
                rtscts=rtscts,
            )
        except Exception as exc:
            self._serial = None
            raise ControllerError(f"{self.label}: failed to open {port}: {exc}") from exc
        self.logger(f"{self.label} connected on {port} @ {baudrate}")

    def disconnect(self) -> None:
        with self._lock:
            if self._serial is not None:
                try:
                    self._serial.close()
                finally:
                    self._serial = None
        self.logger(f"{self.label} disconnected")

    def cancel_pending_io(self) -> None:
        # pyserial supports cancel_read on Windows and POSIX. Prefer it over
        # closing the port because closing during a Windows overlapped read can
        # surface pyserial internals such as "'NoneType' object has no attribute
        # 'hEvent'".
        ser = self._serial
        if ser is None:
            return
        cancelled = False
        try:
            cancel_read = getattr(ser, "cancel_read", None)
            if callable(cancel_read):
                cancel_read()
                cancelled = True
        except Exception:
            pass
        try:
            cancel_write = getattr(ser, "cancel_write", None)
            if callable(cancel_write):
                cancel_write()
        except Exception:
            pass
        if cancelled:
            return
        try:
            ser.close()
            self._serial = None
        except Exception:
            pass

    def send_command(self, command: str, read_reply: bool = True) -> str:
        with self._lock:
            if self.is_cancelled():
                raise ControllerError(f"{self.label}: operation cancelled")
            if not self.is_open:
                raise ControllerError(f"{self.label}: serial port is not connected")
            payload = command.rstrip("\r\n") + self.terminator
            self.logger(f"{self.label} >> {command}")
            try:
                self._serial.write(payload.encode("ascii"))
                if not read_reply:
                    return ""
                reply = self._serial.readline().decode("ascii", errors="replace").strip()
            except Exception as exc:
                if self.is_cancelled() or "hEvent" in str(exc):
                    raise ControllerError(f"{self.label}: operation cancelled") from exc
                raise ControllerError(f"{self.label}: command failed: {exc}") from exc
            if self.is_cancelled():
                raise ControllerError(f"{self.label}: operation cancelled")
            self.logger(f"{self.label} << {reply}")
            return reply


class BaseController:
    key = ""
    label = ""
    axis_count = 0

    def __init__(self, connection: SerialConnection) -> None:
        self.connection = connection
        self.active_axes: set[int] = set()
        self.identity = ""

    def connect(self, **settings) -> None:
        self.connection.connect(**settings)
        self.after_connect()

    def after_connect(self) -> None:
        pass

    def disconnect(self) -> None:
        self.connection.disconnect()
        self.active_axes.clear()

    def selected_active_axes(self, axes: Iterable[int]) -> list[int]:
        selected = sorted(set(axes))
        return [axis for axis in selected if axis in self.active_axes]

    def detect_active_axes(self) -> set[int]:
        raise NotImplementedError

    def refresh_status(self) -> dict[int, dict[str, str | bool]]:
        raise NotImplementedError

    def build_relative_move(self, axes: Iterable[int], distance: str) -> str:
        raise NotImplementedError

    def build_absolute_move(self, axes: Iterable[int], distance: str) -> str:
        raise NotImplementedError

    def build_home(self, axes: Iterable[int]) -> str:
        raise NotImplementedError

    def build_jog(self, axes: Iterable[int], direction: str) -> str:
        raise NotImplementedError

    def build_stop(self, axes: Iterable[int]) -> str:
        raise NotImplementedError

    def build_speed(self, axis: int, slow: str, fast: str, rate: str) -> str:
        raise NotImplementedError

    def emergency_stop(self) -> str:
        return "L:E"

    def set_active_axes(self) -> set[int]:
        self.active_axes = self.detect_active_axes()
        return self.active_axes

    def send(self, command: str) -> str:
        return self.connection.send_command(command)

    def send_ok_command(self, command: str) -> str:
        reply = self.send(command)
        if reply and reply.upper() not in {"OK", "OK_D"}:
            raise ControllerError(f"{self.label}: {command} returned {reply!r}")
        return reply


class HitMvController(BaseController):
    key = "hitmv"
    label = "HIT-MV"
    axis_count = 8

    def detect_active_axes(self) -> set[int]:
        # !: gives busy/ready and blanks for disconnected slave units in HIT mode.
        busy_reply = self.send("!:")
        fields = split_reply(busy_reply, self.axis_count)
        active = {idx + 1 for idx, value in enumerate(fields) if value.strip() != ""}
        if active:
            return active
        # Fallback to Q: if !: does not expose the connected axes on a given setup.
        position_reply = self.send("Q:")
        fields = split_reply(position_reply, self.axis_count)
        return {idx + 1 for idx, value in enumerate(fields) if value.strip() != ""}

    def refresh_status(self) -> dict[int, dict[str, str | bool]]:
        position_fields = split_reply(self.send("Q:"), self.axis_count)
        busy_fields = split_reply(self.send("!:"), self.axis_count)
        detail_reply = self.send("Q:S")
        detail_fields = split_reply(detail_reply, self.axis_count + 1)
        if len(detail_fields) == self.axis_count + 1:
            detail_fields = detail_fields[1:]
        else:
            detail_fields = split_reply(detail_reply, self.axis_count)

        status: dict[int, dict[str, str | bool]] = {}
        for index in range(self.axis_count):
            axis = index + 1
            pos = position_fields[index].strip()
            busy = busy_fields[index].strip()
            detail = detail_fields[index].strip() if index < len(detail_fields) else ""
            active = pos != "" or busy != "" or detail != "" or axis in self.active_axes
            ready = ""
            if busy == "0":
                ready = "Ready"
            elif busy == "1":
                ready = "Busy"
            status[axis] = {
                "active": active,
                "position": pos,
                "ready": ready,
                "detail_status": detail,
            }
        self.active_axes = {axis for axis, values in status.items() if values["active"]}
        return status

    def _vector(self, axes: Iterable[int], value_factory: Callable[[int], str]) -> list[str]:
        selected = set(axes)
        return [value_factory(axis) if axis in selected else "" for axis in range(1, self.axis_count + 1)]

    def build_relative_move(self, axes: Iterable[int], distance: str) -> str:
        value = validate_integer_text(distance, signed=True)
        return "M:" + ",".join(self._vector(axes, lambda _axis: value))

    def build_absolute_move(self, axes: Iterable[int], distance: str) -> str:
        value = validate_integer_text(distance, signed=True)
        return "A:" + ",".join(self._vector(axes, lambda _axis: value))

    def build_home(self, axes: Iterable[int]) -> str:
        return "H:" + ",".join(self._vector(axes, lambda _axis: "1"))

    def build_jog(self, axes: Iterable[int], direction: str) -> str:
        if direction not in {"+", "-"}:
            raise ValueError("Jog direction must be '+' or '-'")
        return "J:" + ",".join(self._vector(axes, lambda _axis: direction))

    def build_stop(self, axes: Iterable[int]) -> str:
        return "L:" + ",".join(self._vector(axes, lambda _axis: "1"))

    def build_speed(self, axis: int, slow: str, fast: str, rate: str) -> str:
        s = validate_integer_text(slow)
        f = validate_integer_text(fast)
        r = validate_integer_text(rate)
        if not 1 <= axis <= self.axis_count:
            raise ValueError(f"HIT-MV axis must be 1-{self.axis_count}")
        return f"D:{axis - 1},{s},{f},{r}"


class Shrc203Controller(BaseController):
    key = "shrc"
    label = "SHRC-203"
    axis_count = 3
    AXIS_MAP = {
        "0": {1},
        "1": {2},
        "2": {3},
        "3": {1, 2},
        "4": {1, 3},
        "5": {2, 3},
        "6": {1, 2, 3},
    }

    def after_connect(self) -> None:
        try:
            self.identity = self.send("*IDN?")
        except ControllerError:
            self.identity = ""

    def detect_active_axes(self) -> set[int]:
        reply = self.send("?:AXIS").strip()
        if reply in self.AXIS_MAP:
            return set(self.AXIS_MAP[reply])
        fields = split_reply(reply, self.axis_count)
        return {idx + 1 for idx, value in enumerate(fields) if value.strip()}

    def refresh_status(self) -> dict[int, dict[str, str | bool]]:
        position_fields = split_reply(self.send("Q:"), self.axis_count)
        busy_fields = split_reply(self.send("!:"), self.axis_count)
        detail_fields = split_reply(self.send("Q:S"), self.axis_count)
        status: dict[int, dict[str, str | bool]] = {}
        for index in range(self.axis_count):
            axis = index + 1
            pos = position_fields[index].strip()
            busy = busy_fields[index].strip()
            detail = detail_fields[index].strip()
            active = axis in self.active_axes or pos != "" or busy != "" or detail != ""
            ready = ""
            if busy == "0":
                ready = "Ready"
            elif busy == "1":
                ready = "Busy"
            status[axis] = {
                "active": active,
                "position": pos,
                "ready": ready,
                "detail_status": detail,
            }
        if not self.active_axes:
            self.active_axes = {axis for axis, values in status.items() if values["active"]}
        return status

    def _vector(self, axes: Iterable[int], value_factory: Callable[[int], str]) -> list[str]:
        selected = set(axes)
        return [value_factory(axis) if axis in selected else "" for axis in range(1, self.axis_count + 1)]

    def build_relative_move(self, axes: Iterable[int], distance: str) -> str:
        value = validate_integer_text(distance, signed=True)
        return "M:" + ",".join(self._vector(axes, lambda _axis: value))

    def build_absolute_move(self, axes: Iterable[int], distance: str) -> str:
        value = validate_integer_text(distance, signed=True)
        return "A:" + ",".join(self._vector(axes, lambda _axis: value))

    def build_home(self, axes: Iterable[int]) -> str:
        return "H:" + ",".join(self._vector(axes, lambda _axis: "1"))

    def build_jog(self, axes: Iterable[int], direction: str) -> str:
        if direction not in {"+", "-"}:
            raise ValueError("Jog direction must be '+' or '-'")
        return "J:" + ",".join(self._vector(axes, lambda _axis: direction))

    def build_stop(self, axes: Iterable[int]) -> str:
        return "L:" + ",".join(self._vector(axes, lambda _axis: "1"))

    def build_speed(self, axis: int, slow: str, fast: str, rate: str) -> str:
        s = validate_integer_text(slow)
        f = validate_integer_text(fast)
        r = validate_integer_text(rate)
        if not 1 <= axis <= self.axis_count:
            raise ValueError(f"SHRC-203 axis must be 1-{self.axis_count}")
        return f"D:{axis},{s},{f},{r}"


@dataclass
class ControllerPanelVars:
    port: tk.StringVar
    baud: tk.StringVar
    timeout: tk.StringVar
    rtscts: tk.BooleanVar
    status: tk.StringVar
    port_combo: ttk.Combobox | None = None


@dataclass
class AxisRowVars:
    state: AxisState
    selected: tk.BooleanVar
    active_text: tk.StringVar
    position: tk.StringVar
    ready: tk.StringVar
    detail: tk.StringVar
    slow: tk.StringVar
    fast: tk.StringVar
    rate: tk.StringVar
    widgets: list[tk.Widget] = field(default_factory=list)
    select_widget: tk.Checkbutton | None = None
    lamp: tk.Label | None = None


class CombinedControllerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Unified HIT-MV + SHRC-203 HIT-Mode Controller")
        self.geometry("1180x760")
        self.minsize(1000, 640)

        self.ui_queue: queue.Queue[Callable[[], None]] = queue.Queue()
        self.cancel_event = threading.Event()
        self.controllers: dict[str, BaseController] = {
            "hitmv": HitMvController(SerialConnection("HIT-MV", self.log, is_cancelled=self.cancel_event.is_set)),
            "shrc": Shrc203Controller(SerialConnection("SHRC-203", self.log, is_cancelled=self.cancel_event.is_set)),
        }
        self.panel_vars: dict[str, ControllerPanelVars] = {}
        self.axis_rows: dict[tuple[str, int], AxisRowVars] = {}
        self.distance_var = tk.StringVar(value="100")
        self.command_busy = False

        self._build_ui()
        self._drain_ui_queue()

    def available_ports(self) -> list[str]:
        if list_ports is None:
            return []
        try:
            return [port.device for port in list_ports.comports()]
        except Exception:
            return []

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=10)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        connection_frame = ttk.LabelFrame(root, text="Communication Settings")
        connection_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        connection_frame.columnconfigure(0, weight=1)
        connection_frame.columnconfigure(1, weight=1)

        self._build_connection_panel(connection_frame, "hitmv", "HIT-MV", "COM3", 0)
        self._build_connection_panel(connection_frame, "shrc", "SHRC-203", "COM28", 1)

        main_pane = ttk.PanedWindow(root, orient=tk.VERTICAL)
        main_pane.grid(row=1, column=0, sticky="nsew")

        top_area = ttk.Frame(main_pane)
        top_area.columnconfigure(0, weight=1)
        top_area.rowconfigure(0, weight=1)
        main_pane.add(top_area, weight=3)

        self._build_axis_table(top_area)
        self._build_motion_panel(root)
        self._build_log(root)

    def _build_connection_panel(
        self,
        parent: ttk.Frame,
        key: str,
        label: str,
        default_port: str,
        column: int,
    ) -> None:
        panel = ttk.Frame(parent, padding=8)
        panel.grid(row=0, column=column, sticky="ew")
        panel.columnconfigure(1, weight=1)

        ports = self.available_ports()
        if default_port not in ports:
            ports = [default_port] + ports

        vars_ = ControllerPanelVars(
            port=tk.StringVar(value=default_port),
            baud=tk.StringVar(value="38400"),
            timeout=tk.StringVar(value="1"),
            rtscts=tk.BooleanVar(value=True),
            status=tk.StringVar(value="Disconnected"),
        )
        self.panel_vars[key] = vars_

        ttk.Label(panel, text=label, font=("", 10, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(panel, textvariable=vars_.status).grid(row=0, column=1, sticky="w")

        ttk.Label(panel, text="Port").grid(row=1, column=0, sticky="w")
        port_combo = ttk.Combobox(panel, textvariable=vars_.port, values=ports, width=14)
        port_combo.grid(row=1, column=1, sticky="ew", padx=4)
        vars_.port_combo = port_combo

        ttk.Label(panel, text="Baud").grid(row=1, column=2, sticky="w")
        ttk.Entry(panel, textvariable=vars_.baud, width=8).grid(row=1, column=3, sticky="w", padx=4)

        ttk.Label(panel, text="Timeout").grid(row=1, column=4, sticky="w")
        ttk.Entry(panel, textvariable=vars_.timeout, width=6).grid(row=1, column=5, sticky="w", padx=4)

        ttk.Checkbutton(panel, text="RTS/CTS", variable=vars_.rtscts).grid(row=1, column=6, sticky="w")
        ttk.Button(panel, text="Connect", command=lambda: self.connect_controller(key)).grid(row=2, column=0, pady=(6, 0), sticky="ew")
        ttk.Button(panel, text="Disconnect", command=lambda: self.disconnect_controller(key)).grid(row=2, column=1, pady=(6, 0), sticky="ew")
        ttk.Button(panel, text="Refresh Status", command=lambda: self.refresh_controller(key)).grid(row=2, column=2, columnspan=2, pady=(6, 0), sticky="ew")
        ttk.Button(panel, text="Scan Ports", command=self.refresh_ports).grid(row=2, column=4, columnspan=2, pady=(6, 0), sticky="ew")

    def _build_axis_table(self, parent: ttk.Frame) -> None:
        table_frame = ttk.LabelFrame(parent, text="Axes")
        table_frame.grid(row=0, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        canvas = tk.Canvas(table_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.axis_table = ttk.Frame(canvas)
        self.axis_table.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.axis_table, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        headers = ["Use", "Active", "Controller", "Axis", "Position", "Ready/Busy", "Detail Status", "Slow", "Fast", "Rate"]
        for col, header in enumerate(headers):
            ttk.Label(self.axis_table, text=header, font=("", 9, "bold")).grid(row=0, column=col, sticky="w", padx=4, pady=3)

        row = 1
        for key, label, count in [("hitmv", "HIT-MV", 8), ("shrc", "SHRC-203", 3)]:
            for axis in range(1, count + 1):
                self._add_axis_row(row, key, label, axis)
                row += 1

    def _add_axis_row(self, row: int, key: str, label: str, axis: int) -> None:
        state = AxisState(key, label, axis, f"{label} {axis}")
        vars_ = AxisRowVars(
            state=state,
            selected=tk.BooleanVar(value=False),
            active_text=tk.StringVar(value=""),
            position=tk.StringVar(value=""),
            ready=tk.StringVar(value=""),
            detail=tk.StringVar(value=""),
            slow=tk.StringVar(value=DEFAULT_SLOW),
            fast=tk.StringVar(value=DEFAULT_FAST),
            rate=tk.StringVar(value=DEFAULT_RATE),
        )

        select = tk.Checkbutton(self.axis_table, variable=vars_.selected, state=tk.DISABLED)
        select.grid(row=row, column=0, sticky="w", padx=4)
        vars_.select_widget = select

        lamp = tk.Label(self.axis_table, text="", width=3, relief=tk.SUNKEN, bg="#d8d8d8")
        lamp.grid(row=row, column=1, sticky="w", padx=4, pady=2)
        vars_.lamp = lamp

        labels = [
            ttk.Label(self.axis_table, text=label),
            ttk.Label(self.axis_table, text=str(axis)),
            ttk.Label(self.axis_table, textvariable=vars_.position, width=16),
            ttk.Label(self.axis_table, textvariable=vars_.ready, width=12),
            ttk.Label(self.axis_table, textvariable=vars_.detail, width=18),
        ]
        for offset, widget in enumerate(labels, start=2):
            widget.grid(row=row, column=offset, sticky="w", padx=4)
            vars_.widgets.append(widget)

        for col, variable in [(7, vars_.slow), (8, vars_.fast), (9, vars_.rate)]:
            entry = ttk.Entry(self.axis_table, textvariable=variable, width=10)
            entry.grid(row=row, column=col, sticky="w", padx=4)
            vars_.widgets.append(entry)

        self.axis_rows[(key, axis)] = vars_
        self._set_axis_active(vars_, False)

    def _build_motion_panel(self, root: ttk.Frame) -> None:
        motion = ttk.LabelFrame(root, text="Movement Controls")
        motion.grid(row=2, column=0, sticky="ew", pady=(8, 8))
        motion.columnconfigure(1, weight=1)

        ttk.Label(motion, text="Native distance").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(motion, textvariable=self.distance_var, width=16).grid(row=0, column=1, sticky="w", padx=6, pady=6)
        ttk.Label(motion, text="No unit conversion; value is sent in each controller's native HIT-mode syntax.").grid(row=0, column=2, columnspan=6, sticky="w", padx=6)

        buttons = [
            ("Relative Move", self.relative_move),
            ("Absolute Move", self.absolute_move),
            ("Home/Origin", self.home_selected),
            ("Set Speed", self.set_speed_selected),
            ("Jog +", lambda: self.jog_selected("+")),
            ("Jog -", lambda: self.jog_selected("-")),
            ("Stop Selected", self.stop_selected),
            ("Emergency Stop All", self.emergency_stop_all),
            ("Cancel Current Operation", self.cancel_current_operation),
        ]
        for col, (text, command) in enumerate(buttons):
            ttk.Button(motion, text=text, command=command).grid(row=1, column=col, padx=4, pady=(0, 6), sticky="ew")

    def _build_log(self, root: ttk.Frame) -> None:
        log_frame = ttk.LabelFrame(root, text="Command Log")
        log_frame.grid(row=3, column=0, sticky="nsew")
        root.rowconfigure(3, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = tk.Text(log_frame, height=9, wrap=tk.NONE)
        y_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=y_scroll.set)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")

    def log(self, message: str) -> None:
        def append() -> None:
            self.log_text.insert(tk.END, f"[{now_stamp()}] {message}\n")
            self.log_text.see(tk.END)

        if threading.current_thread() is threading.main_thread():
            append()
        else:
            self.ui_queue.put(append)

    def _set_busy(self, busy: bool) -> None:
        self.command_busy = busy
        self.config(cursor="watch" if busy else "")

    def _run_worker(self, title: str, work: Callable[[], None]) -> None:
        if self.command_busy:
            self.log("Another command is still running.")
            return
        self.cancel_event.clear()
        self._set_busy(True)

        def target() -> None:
            try:
                work()
            except Exception as exc:
                if self.cancel_event.is_set():
                    self.log(f"{title}: cancelled")
                else:
                    self.ui_queue.put(lambda exc=exc: messagebox.showerror(title, str(exc)))
                    self.log(f"ERROR: {exc}")
            finally:
                self.ui_queue.put(lambda: self._set_busy(False))

        threading.Thread(target=target, daemon=True).start()

    def refresh_ports(self) -> None:
        ports = self.available_ports()
        defaults = {"hitmv": "COM3", "shrc": "COM28"}
        for key, vars_ in self.panel_vars.items():
            current = vars_.port.get().strip()
            values = list(ports)
            for candidate in [current, defaults[key]]:
                if candidate and candidate not in values:
                    values.insert(0, candidate)
            if vars_.port_combo is not None:
                vars_.port_combo.configure(values=values)
            if not current and values:
                vars_.port.set(values[0])
        self.log("Scanned available COM ports: " + (", ".join(ports) if ports else "none found"))

    def cancel_current_operation(self) -> None:
        self.cancel_event.set()
        for controller in self.controllers.values():
            controller.connection.cancel_pending_io()
        self.log("Cancel requested. Pending serial reads were interrupted when possible.")

    def _drain_ui_queue(self) -> None:
        try:
            while True:
                callback = self.ui_queue.get_nowait()
                callback()
        except queue.Empty:
            pass
        self.after(50, self._drain_ui_queue)

    def connect_controller(self, key: str) -> None:
        vars_ = self.panel_vars[key]
        controller = self.controllers[key]

        def work() -> None:
            controller.connect(
                port=vars_.port.get().strip(),
                baudrate=int(vars_.baud.get().strip()),
                timeout=float(vars_.timeout.get().strip()),
                rtscts=vars_.rtscts.get(),
            )
            active = controller.set_active_axes()
            status = controller.refresh_status()
            self.ui_queue.put(lambda: self._apply_controller_status(key, active, status, "Connected"))

        self._run_worker(f"Connect {controller.label}", work)

    def disconnect_controller(self, key: str) -> None:
        controller = self.controllers[key]

        def work() -> None:
            controller.disconnect()
            self.ui_queue.put(lambda: self._clear_controller_status(key))

        self._run_worker(f"Disconnect {controller.label}", work)

    def refresh_controller(self, key: str) -> None:
        controller = self.controllers[key]

        def work() -> None:
            active = controller.set_active_axes()
            status = controller.refresh_status()
            self.ui_queue.put(lambda: self._apply_controller_status(key, active, status, "Connected"))

        self._run_worker(f"Refresh {controller.label}", work)

    def _apply_controller_status(
        self,
        key: str,
        active_axes: set[int],
        status: dict[int, dict[str, str | bool]],
        panel_status: str,
    ) -> None:
        self.panel_vars[key].status.set(panel_status)
        for axis in range(1, self.controllers[key].axis_count + 1):
            row = self.axis_rows[(key, axis)]
            values = status.get(axis, {})
            active = bool(values.get("active", axis in active_axes))
            row.position.set(str(values.get("position", "")))
            row.ready.set(str(values.get("ready", "")))
            row.detail.set(str(values.get("detail_status", "")))
            self._set_axis_active(row, active)

    def _clear_controller_status(self, key: str) -> None:
        self.panel_vars[key].status.set("Disconnected")
        for axis in range(1, self.controllers[key].axis_count + 1):
            row = self.axis_rows[(key, axis)]
            row.position.set("")
            row.ready.set("")
            row.detail.set("")
            row.selected.set(False)
            self._set_axis_active(row, False)

    def _set_axis_active(self, row: AxisRowVars, active: bool) -> None:
        row.state.active = active
        if row.lamp is not None:
            row.lamp.configure(bg="#1fb55a" if active else "#d8d8d8")
        if row.select_widget is not None:
            row.select_widget.configure(state=tk.NORMAL if active else tk.DISABLED)
        state = tk.NORMAL if active else tk.DISABLED
        for widget in row.widgets:
            if isinstance(widget, ttk.Entry):
                widget.configure(state=state)

    def selected_axes_by_controller(self) -> dict[str, list[int]]:
        selected: dict[str, list[int]] = {"hitmv": [], "shrc": []}
        for (key, axis), row in self.axis_rows.items():
            if row.selected.get() and row.state.active:
                selected[key].append(axis)
        return selected

    def _send_grouped_commands(
        self,
        title: str,
        builder: Callable[[BaseController, list[int]], list[str]],
        refresh_after: bool = True,
    ) -> None:
        selected = self.selected_axes_by_controller()
        if not any(selected.values()):
            messagebox.showwarning(title, "Select at least one active axis.")
            return

        def work() -> None:
            for key in ["hitmv", "shrc"]:
                axes = selected[key]
                if not axes:
                    continue
                controller = self.controllers[key]
                for command in builder(controller, axes):
                    controller.send_ok_command(command)
            if refresh_after:
                time.sleep(0.1)
                for key in ["hitmv", "shrc"]:
                    if selected[key]:
                        controller = self.controllers[key]
                        status = controller.refresh_status()
                        active = set(controller.active_axes)
                        self.ui_queue.put(lambda key=key, active=active, status=status: self._apply_controller_status(key, active, status, "Connected"))

        self._run_worker(title, work)

    def relative_move(self) -> None:
        distance = self.distance_var.get()
        self._send_grouped_commands(
            "Relative Move",
            lambda controller, axes: [controller.build_relative_move(axes, distance)],
        )

    def absolute_move(self) -> None:
        distance = self.distance_var.get()
        self._send_grouped_commands(
            "Absolute Move",
            lambda controller, axes: [controller.build_absolute_move(axes, distance)],
        )

    def home_selected(self) -> None:
        self._send_grouped_commands(
            "Home/Origin",
            lambda controller, axes: [controller.build_home(axes)],
        )

    def jog_selected(self, direction: str) -> None:
        self._send_grouped_commands(
            f"Jog {direction}",
            lambda controller, axes: [controller.build_jog(axes, direction)],
        )

    def stop_selected(self) -> None:
        self._send_grouped_commands(
            "Stop Selected",
            lambda controller, axes: [controller.build_stop(axes)],
        )

    def set_speed_selected(self) -> None:
        selected = self.selected_axes_by_controller()
        if not any(selected.values()):
            messagebox.showwarning("Set Speed", "Select at least one active axis.")
            return

        def builder(controller: BaseController, axes: list[int]) -> list[str]:
            commands = []
            for axis in axes:
                row = self.axis_rows[(controller.key, axis)]
                commands.append(controller.build_speed(axis, row.slow.get(), row.fast.get(), row.rate.get()))
            return commands

        self._send_grouped_commands("Set Speed", builder, refresh_after=False)

    def emergency_stop_all(self) -> None:
        def work() -> None:
            for key in ["hitmv", "shrc"]:
                controller = self.controllers[key]
                if controller.connection.is_open:
                    controller.send_ok_command(controller.emergency_stop())

        self._run_worker("Emergency Stop All", work)


def main() -> None:
    app = CombinedControllerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
