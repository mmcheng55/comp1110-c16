"""
network_view.py
---------------
Interactive map view for the transport network.
"""
import tkinter as tk
from tkinter import ttk
import re

# ── Line colour palette (matches route_card.py) ──────────────────────────────
_LINE_COLOURS: dict[str, str] = {
    "AEL": "#007DC5",
    "TCL": "#F7943E",
    "TML": "#9A3B26",
    "TKL": "#7D499D",
    "EAL": "#53B7E8",
    "SIL": "#CBD300",
    "KTL": "#1CAF49",
    "TWL": "#E2231A",
    "ISL": "#007DC5",
    "DRL": "#EA0070",
}
_FALLBACK_COLOURS = [
    "#4A90D9", "#E67E22", "#8E44AD", "#27AE60",
    "#C0392B", "#2980B9", "#D35400", "#16A085",
    "#795548", "#607D8B",
]
_STOP_RADIUS = 5          # px, normal stop circle
_STOP_RADIUS_HOVER = 8    # px, enlarged on hover
_STOP_COLOUR = "#FFFFFF"
_STOP_OUTLINE = "#333333"
_BG = "#1C2330"           # dark map background
_EDGE_WIDTH = 2
_MARGIN = 48              # canvas margin so nodes aren't clipped


def _line_colour(line: str, index: int) -> str:
    upper = line.upper()
    if upper in _LINE_COLOURS:
        return _LINE_COLOURS[upper]
    return _FALLBACK_COLOURS[index % len(_FALLBACK_COLOURS)]


def _format_stop_name(stop_name: str) -> str:
    words = re.findall(r"[A-Z]+(?=$|[A-Z][a-z])|[A-Z]?[a-z]+", stop_name)
    return " ".join(words) if words else stop_name


class NetworkView(tk.Toplevel):
    """
    A pop-up window that renders the transit network as an interactive map.

    Parameters
    ----------
    network_data : dict
        Raw network dict with keys ``stops`` and ``segments``.
    """

    def __init__(self, parent, network_data: dict):
        super().__init__(parent)
        self.title("Transit Network Map")
        self.geometry("900x640")
        self.minsize(600, 400)
        self.configure(bg=_BG)

        self._network_data = network_data
        self._line_index: dict[str, int] = {}   # line_code -> colour index
        self._stop_positions: dict[str, tuple[float, float]] = {}  # stopName -> (nx, ny)
        self._stop_canvas_pos: dict[str, tuple[float, float]] = {}  # stopName -> (cx, cy)
        self._stop_items: dict[str, int] = {}    # stopName -> canvas oval item id
        self._hover_tag: int | None = None
        self._tooltip: tk.Label | None = None
        self._selected_stop: str | None = None

        self._build_ui()
        self._preprocess()
        self.bind("<Configure>", self._on_resize)
        self.after(100, self._draw)  # defer until window is actually laid out

    # ── UI skeleton ──────────────────────────────────────────────────────────

    def _build_ui(self):
        # Top toolbar
        toolbar = tk.Frame(self, bg="#111827", pady=6)
        toolbar.pack(fill="x", side="top")
        tk.Label(
            toolbar, text="Transit Network", bg="#111827", fg="#E5E7EB",
            font=("Helvetica", 13, "bold"), padx=12,
        ).pack(side="left")
        ttk.Button(toolbar, text="✕  Close", command=self.destroy).pack(side="right", padx=10)

        # Legend frame (bottom)
        self._legend_frame = tk.Frame(self, bg="#111827")
        self._legend_frame.pack(fill="x", side="bottom")

        # Canvas (fills remaining space)
        self.canvas = tk.Canvas(self, bg=_BG, highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.canvas.bind("<Leave>", self._on_mouse_leave)
        self.canvas.bind("<Button-1>", self._on_click)

    # ── Data pre-processing ──────────────────────────────────────────────────

    def _preprocess(self):
        stops_raw = self._network_data.get("stops") or self._network_data.get("allStops") or []
        for stop in stops_raw:
            if not isinstance(stop, dict):
                continue
            name = stop.get("stopName")
            pos = (
                stop.get("normalizedPositionOnScreen")
                or stop.get("segmentTransportationType")
                or {}
            )
            if isinstance(pos, dict):
                x, y = float(pos.get("x", 0.0)), float(pos.get("y", 0.0))
            elif isinstance(pos, (list, tuple)) and len(pos) >= 2:
                x, y = float(pos[0]), float(pos[1])
            else:
                x, y = 0.0, 0.0
            if name:
                self._stop_positions[name] = (x, y)

        # Build line index (for colour assignment)
        segs = self._network_data.get("segments") or self._network_data.get("allSegments") or []
        idx = 0
        for seg in segs:
            if not isinstance(seg, dict):
                continue
            line = (
                seg.get("line") or seg.get("lineCode")
                or seg.get("routeName") or seg.get("route")
            )
            if line and str(line) not in self._line_index:
                self._line_index[str(line)] = idx
                idx += 1

    # ── Drawing ──────────────────────────────────────────────────────────────

    def _on_resize(self, _event=None):
        self.after_cancel(getattr(self, "_resize_job", None) or self.after(0, lambda: None))
        self._resize_job = self.after(80, self._draw)

    def _draw(self):
        self.canvas.delete("all")
        self._stop_items.clear()
        self._stop_canvas_pos.clear()
        self._hover_tag = None

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 10 or ch < 10:
            return

        draw_w = cw - 2 * _MARGIN
        draw_h = ch - 2 * _MARGIN

        def to_canvas(nx: float, ny: float) -> tuple[float, float]:
            return _MARGIN + nx * draw_w, _MARGIN + ny * draw_h

        # Pre-compute canvas positions for all stops
        for name, (nx, ny) in self._stop_positions.items():
            cx, cy = to_canvas(nx, ny)
            self._stop_canvas_pos[name] = (cx, cy)

        # ── Draw edges ───────────────────────────────────────────────
        segs = self._network_data.get("segments") or self._network_data.get("allSegments") or []
        drawn_edges: set[tuple[str, str, str]] = set()
        for seg in segs:
            if not isinstance(seg, dict):
                continue
            line = str(
                seg.get("line") or seg.get("lineCode")
                or seg.get("routeName") or seg.get("route") or ""
            )
            from_d = seg.get("from") or seg.get("fromStop") or {}
            to_d = seg.get("to") or seg.get("toStop") or {}
            if not isinstance(from_d, dict) or not isinstance(to_d, dict):
                continue
            from_name = from_d.get("stopName", "")
            to_name = to_d.get("stopName", "")
            if not from_name or not to_name:
                continue

            # Deduplicate undirected edges per line
            edge_key = (line, min(from_name, to_name), max(from_name, to_name))
            if edge_key in drawn_edges:
                continue
            drawn_edges.add(edge_key)

            from_pos = self._stop_canvas_pos.get(from_name)
            to_pos = self._stop_canvas_pos.get(to_name)
            if from_pos is None or to_pos is None:
                continue

            colour = _line_colour(line, self._line_index.get(line, 0))
            self.canvas.create_line(
                from_pos[0], from_pos[1],
                to_pos[0], to_pos[1],
                fill=colour, width=_EDGE_WIDTH, tags=("edge",),
            )

        # ── Draw stops ───────────────────────────────────────────────
        for name, (cx, cy) in self._stop_canvas_pos.items():
            r = _STOP_RADIUS
            item = self.canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                fill=_STOP_COLOUR, outline=_STOP_OUTLINE, width=1,
                tags=("stop", f"stop:{name}"),
            )
            self._stop_items[name] = item

        # ── Legend ───────────────────────────────────────────────────
        self._rebuild_legend()

    def _rebuild_legend(self):
        for widget in self._legend_frame.winfo_children():
            widget.destroy()

        tk.Label(
            self._legend_frame, text="Lines:", bg="#111827", fg="#9CA3AF",
            font=("Helvetica", 10, "bold"), padx=8,
        ).pack(side="left", pady=4)

        for line, idx in sorted(self._line_index.items(), key=lambda kv: kv[0]):
            colour = _line_colour(line, idx)
            entry = tk.Frame(self._legend_frame, bg="#111827")
            entry.pack(side="left", padx=6, pady=4)
            tk.Canvas(entry, width=14, height=14, bg=colour, highlightthickness=0).pack(side="left")
            tk.Label(
                entry, text=line, bg="#111827", fg="#E5E7EB",
                font=("Helvetica", 9),
            ).pack(side="left", padx=(2, 0))

    # ── Interaction ───────────────────────────────────────────────────────────

    def _find_nearest_stop(self, mx: float, my: float, threshold: float = 12.0) -> str | None:
        best_name, best_dist = None, threshold
        for name, (cx, cy) in self._stop_canvas_pos.items():
            dist = ((mx - cx) ** 2 + (my - cy) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best_name = name
        return best_name

    def _on_mouse_move(self, event):
        stop = self._find_nearest_stop(event.x, event.y)
        self._show_tooltip(stop, event.x, event.y)
        self._highlight_stop(stop)

    def _on_mouse_leave(self, _event=None):
        self._hide_tooltip()
        self._highlight_stop(None)

    def _on_click(self, event):
        stop = self._find_nearest_stop(event.x, event.y)
        if stop:
            self._selected_stop = stop if self._selected_stop != stop else None
            self._refresh_selection()

    def _refresh_selection(self):
        # Reset all stops to default appearance
        for name, item in self._stop_items.items():
            r = _STOP_RADIUS
            cx, cy = self._stop_canvas_pos[name]
            self.canvas.coords(item, cx - r, cy - r, cx + r, cy + r)
            self.canvas.itemconfigure(item, fill=_STOP_COLOUR, outline=_STOP_OUTLINE, width=1)
        # Highlight selected
        if self._selected_stop and self._selected_stop in self._stop_items:
            item = self._stop_items[self._selected_stop]
            cx, cy = self._stop_canvas_pos[self._selected_stop]
            r = _STOP_RADIUS_HOVER + 2
            self.canvas.coords(item, cx - r, cy - r, cx + r, cy + r)
            self.canvas.itemconfigure(item, fill="#FACC15", outline="#F59E0B", width=2)
            self.canvas.tag_raise(item)

    def _highlight_stop(self, name: str | None):
        # Undo previous hover highlight (unless it's the selected stop)
        if self._hover_tag and self._hover_tag in self._stop_items.values():
            hover_name = next(
                (n for n, i in self._stop_items.items() if i == self._hover_tag), None
            )
            if hover_name and hover_name != self._selected_stop:
                item = self._hover_tag
                cx, cy = self._stop_canvas_pos[hover_name]
                r = _STOP_RADIUS
                self.canvas.coords(item, cx - r, cy - r, cx + r, cy + r)
                self.canvas.itemconfigure(item, fill=_STOP_COLOUR, outline=_STOP_OUTLINE, width=1)

        self._hover_tag = None
        if name and name != self._selected_stop and name in self._stop_items:
            item = self._stop_items[name]
            cx, cy = self._stop_canvas_pos[name]
            r = _STOP_RADIUS_HOVER
            self.canvas.coords(item, cx - r, cy - r, cx + r, cy + r)
            self.canvas.itemconfigure(item, fill="#60A5FA", outline="#3B82F6", width=2)
            self.canvas.tag_raise(item)
            self._hover_tag = item

    def _show_tooltip(self, name: str | None, mx: float, my: float):
        self._hide_tooltip()
        if not name:
            return
        label = _format_stop_name(name)
        # Find which lines serve this stop
        segs = self._network_data.get("segments") or []
        lines_at_stop: set[str] = set()
        for seg in segs:
            if not isinstance(seg, dict):
                continue
            line = seg.get("line") or seg.get("lineCode") or ""
            from_d = seg.get("from") or seg.get("fromStop") or {}
            to_d = seg.get("to") or seg.get("toStop") or {}
            if isinstance(from_d, dict) and from_d.get("stopName") == name:
                if line:
                    lines_at_stop.add(str(line))
            if isinstance(to_d, dict) and to_d.get("stopName") == name:
                if line:
                    lines_at_stop.add(str(line))

        line_text = f"  Lines: {', '.join(sorted(lines_at_stop))}" if lines_at_stop else ""
        tip_text = f"  {label}{line_text}  "

        tip = tk.Label(
            self.canvas,
            text=tip_text,
            bg="#1F2937",
            fg="#F9FAFB",
            font=("Helvetica", 10),
            relief="flat",
            bd=0,
            padx=4,
            pady=3,
        )
        # Position tooltip so it doesn't go off-screen
        tx = min(mx + 14, self.canvas.winfo_width() - 180)
        ty = max(my - 32, 4)
        tip.place(x=tx, y=ty)
        self._tooltip = tip

    def _hide_tooltip(self):
        if self._tooltip:
            self._tooltip.destroy()
            self._tooltip = None
