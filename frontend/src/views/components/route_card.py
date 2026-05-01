"""
route_card.py
-------------
UI component for displaying a summary of a transport route.
"""
import tkinter as tk
from tkinter import ttk

# MTR line colour palette (code -> hex).  Unknown lines get a neutral grey.
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
]

_PILL_H = 22       # pill height in px
_PILL_PAD_X = 10   # horizontal padding inside pill
_PILL_MIN_W = 44   # minimum pill width
_ARROW_W = 20      # width reserved for the "→" arrow between pills
_FONT_PILL = ("Helvetica", 10, "bold")
_FONT_STAT_LABEL = ("Helvetica", 10, "bold")
_FONT_STAT_VALUE = ("Helvetica", 13)
_FONT_RANK_LABEL = ("Helvetica", 10, "bold")
_FONT_RANK_VALUE = ("Helvetica", 18, "bold")
_FONT_DESC = ("Helvetica", 13, "bold")
_FONT_SUMMARY = ("Helvetica", 11)


def _line_colour(line: str, index: int) -> str:
    upper = line.upper()
    if upper in _LINE_COLOURS:
        return _LINE_COLOURS[upper]
    # Dynamically apply colour based on hash of line name to keep it consistent
    hash_val = sum(ord(c) for c in upper)
    return _FALLBACK_COLOURS[hash_val % len(_FALLBACK_COLOURS)]


def _contrast_text(hex_colour: str) -> str:
    """Return black or white depending on background luminance."""
    hex_colour = hex_colour.lstrip("#")
    r, g, b = int(hex_colour[0:2], 16), int(hex_colour[2:4], 16), int(hex_colour[4:6], 16)
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return "#000000" if luminance > 160 else "#FFFFFF"


class RouteCard(tk.Canvas):
    """A custom Tkinter Canvas acting as an interactive card for a route.

    Displays the route rank, description, statistical summaries, and visual
    pills representing the line sequence.

    Parameters
    ----------
    parent : tk.Widget
        The parent widget.
    rank : int
        The overall rank/position of this route.
    description : str
        Textual path description (e.g., "A -> B -> C").
    total_cost : float | None
        Total fare in dollars.
    total_distance_km : float | None
        Total distance in kilometers.
    travel_time_minutes : float | None
        Estimated travel time in minutes.
    transfer_count : int | None
        Number of line or mode transfers required.
    score : float | None
        Calculated route score.
    transfer_summary : str
        Short text describing the transfer sequence (e.g., "Direct", "Interchange: TWL -> KTL").
    on_select : callable
        Callback fired when the card is clicked.
    lines : list[str] | None
        Ordered list of line codes to render as visual pills.
    **kwargs
        Additional arguments passed to `tk.Canvas`.
    """
    def __init__(
        self,
        parent,
        rank: int,
        description: str,
        total_cost: float | None,
        total_distance_km: float | None,
        travel_time_minutes: float | None,
        transfer_count: int | None,
        score: float | None,
        transfer_summary: str,
        on_select,
        # Ordered list of line codes used in this route
        lines: list | None = None,
        **kwargs,
    ):
        background = ttk.Style().lookup("TFrame", "background") or "white"
        # Extra height when we have line pills to show
        card_height = 210 if lines else 188
        super().__init__(parent, height=card_height, highlightthickness=0, bg=background, **kwargs)

        self.rank = rank
        self.description = description
        self.total_cost = total_cost
        self.total_distance_km = total_distance_km
        self.travel_time_minutes = travel_time_minutes
        self.transfer_count = transfer_count
        self.score = score
        self.transfer_summary = transfer_summary
        self.on_select = on_select
        self.lines = lines or []

        self.bind("<Configure>", self._redraw)
        self.bind("<Button-1>", self._on_select)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def _redraw(self, _event=None):
        self.delete("all")
        width = max(self.winfo_width(), 20)
        height = max(self.winfo_height(), 20)
        radius = 18
        left_split = max(width * 0.16, 72)
        content_left = left_split + 22
        content_right = width - 24
        content_width = max(content_right - content_left, 120)

        # Card background
        self._rounded_rect(4, 4, width - 4, height - 4, radius, fill="#F2F4F8", outline="#CBD3DC")
        self.create_line(left_split, 12, left_split, height - 12, fill="#CBD3DC", width=1)

        # ── Rank panel ──────────────────────────────────────────────
        self.create_text(
            left_split / 2, 52,
            text="Rank",
            font=_FONT_RANK_LABEL,
            fill="#5A6775",
        )
        self.create_text(
            left_split / 2, height / 2 + 10,
            text=f"#{self.rank}",
            font=_FONT_RANK_VALUE,
            fill="#1A1A1A",
        )

        # ── Route description ────────────────────────────────────────
        desc_id = self.create_text(
            content_left, 24,
            text=self._format_route_path(width),
            width=content_width,
            justify="left",
            anchor="nw",
            font=_FONT_DESC,
            fill="#004A99",
            tags=("card",),
        )
        
        # Get actual height of description text to avoid overlap
        desc_bbox = self.bbox(desc_id)
        desc_bottom = desc_bbox[3] if desc_bbox else 42

        # ── Transfer / line pills ────────────────────────────────────
        pills_top = max(74, desc_bottom + 16)
        if self.lines:
            pills_bot = self._draw_line_pills(content_left, pills_top, content_right)
            summary_top = pills_bot + 8
        else:
            summary_top = pills_top + 10

        summary_id = self.create_text(
            content_left, summary_top,
            text=self.transfer_summary,
            width=content_width,
            justify="left",
            anchor="nw",
            font=_FONT_SUMMARY,
            fill="#5A6775",
            tags=("card",),
        )

        summary_bbox = self.bbox(summary_id)
        summary_bottom = summary_bbox[3] if summary_bbox else summary_top + 20

        # Calculate where stats should go to avoid overlap
        stats_top = max(height - 58, summary_bottom + 16)
        
        # If the required height is larger than the current canvas height, configure it
        required_height = stats_top + 58
        if required_height > self.winfo_height() and self.winfo_height() > 1:
            self.configure(height=required_height)
            # Re-draw the card outline to cover the new height
            self._rounded_rect(4, 4, width - 4, required_height - 4, radius, fill="#F2F4F8", outline="#CBD3DC")
            self.create_line(left_split, 12, left_split, required_height - 12, fill="#CBD3DC", width=1)
            self.create_line(content_left, stats_top, content_right, stats_top, fill="#CBD3DC", width=1)
            # Also re-center the Rank
            self.create_text(
                left_split / 2, required_height / 2 + 10,
                text=f"#{self.rank}",
                font=_FONT_RANK_VALUE,
                fill="#1A1A1A",
            )
        else:
            self.create_line(content_left, stats_top, content_right, stats_top, fill="#CBD3DC", width=1)

        # ── Stats row ────────────────────────────────────────────────
        stat_width = (content_right - content_left) / 5
        self._draw_stat(content_left + stat_width * 0.5, stats_top + 10, "Fare",      self._format_cost(),      tags=("card",))
        self._draw_stat(content_left + stat_width * 1.5, stats_top + 10, "Time",      self._format_time(),      tags=("card",))
        self._draw_stat(content_left + stat_width * 2.5, stats_top + 10, "Distance",  self._format_distance(),  tags=("card",))
        self._draw_stat(content_left + stat_width * 3.5, stats_top + 10, "Transfers", self._format_transfers(), tags=("card",))
        self._draw_stat(content_left + stat_width * 4.5, stats_top + 10, "Score",     self._format_score(),     tags=("card",))

        self.tag_bind("card", "<Button-1>", self._on_select)

    def _draw_line_pills(self, x_start: float, y: float, x_end: float) -> float:
        """Draw coloured pill badges for each line, connected by arrows. Returns the bottom Y coordinate."""
        if not self.lines:
            return y

        display_data = []
        for line_obj in self.lines:
            if isinstance(line_obj, dict):
                line = line_obj.get("line", "")
                mode = line_obj.get("mode", "Train")
            else:
                line = str(line_obj)
                mode = "Train"
            
            icon = "🚆" if "train" in mode.lower() else ("🚌" if "bus" in mode.lower() else "🚶")
            disp_line = line.upper()
            if len(disp_line) > 16:
                disp_line = disp_line[:14] + ".."
            display_text = f"{icon} {disp_line}"
            display_data.append((line, display_text))

        pill_h = _PILL_H
        cursor_x = x_start
        cursor_y = y

        for i, (line, display_text) in enumerate(display_data):
            colour = _line_colour(line, i)
            text_colour = _contrast_text(colour)
            pill_w = max(_PILL_MIN_W, len(display_text) * 8 + _PILL_PAD_X * 2)

            if cursor_x + pill_w > x_end and cursor_x > x_start:
                cursor_x = x_start
                cursor_y += pill_h + 10

            self._rounded_rect(
                cursor_x, cursor_y,
                cursor_x + pill_w, cursor_y + pill_h,
                radius=pill_h // 2,
                fill=colour,
                outline=colour,
                tags=("card",),
            )
            self.create_text(
                cursor_x + pill_w / 2,
                cursor_y + pill_h / 2,
                text=display_text,
                font=_FONT_PILL,
                fill=text_colour,
                tags=("card",),
            )
            cursor_x += pill_w

            if i < len(self.lines) - 1:
                if cursor_x + _ARROW_W > x_end:
                    cursor_x = x_start
                    cursor_y += pill_h + 10
                
                if cursor_x > x_start:
                    arrow_cx = cursor_x + _ARROW_W / 2
                    arrow_cy = cursor_y + pill_h / 2
                    self.create_text(
                        arrow_cx, arrow_cy,
                        text="→",
                        font=("Helvetica", 12),
                        fill="#5A6775",
                        tags=("card",),
                    )
                    cursor_x += _ARROW_W

        return cursor_y + pill_h

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _on_select(self, _event=None):
        self.on_select()

    # ------------------------------------------------------------------
    # Stat helper
    # ------------------------------------------------------------------

    def _draw_stat(self, center_x, top_y, label: str, value: str, **kwargs):
        self.create_text(center_x, top_y,      text=label, font=_FONT_STAT_LABEL, fill="#5A6775", anchor="n", **kwargs)
        self.create_text(center_x, top_y + 24, text=value, font=_FONT_STAT_VALUE, fill="#1A1A1A", anchor="n", **kwargs)

    # ------------------------------------------------------------------
    # Formatters
    # ------------------------------------------------------------------

    def _format_cost(self) -> str:
        return "N/A" if self.total_cost is None else f"${self.total_cost:.2f}"

    def _format_distance(self) -> str:
        return "N/A" if self.total_distance_km is None else f"{self.total_distance_km:.1f} km"

    def _format_time(self) -> str:
        if self.travel_time_minutes is None:
            return "Unavailable"
        if self.travel_time_minutes < 60:
            return f"{self.travel_time_minutes:.0f} min"
        hours = int(self.travel_time_minutes // 60)
        minutes = int(self.travel_time_minutes % 60)
        return f"{hours}h {minutes}m" if minutes else f"{hours}h"

    def _format_transfers(self) -> str:
        return "N/A" if self.transfer_count is None else str(self.transfer_count)

    def _format_score(self) -> str:
        return "N/A" if self.score is None else f"{self.score:.2f}"

    def _format_route_path(self, width: int) -> str:
        stops = [part.strip() for part in self.description.split("->") if part.strip()]
        if len(stops) <= 2:
            return " → ".join(stops) if stops else self.description
        if width < 560:
            return f"{stops[0]} → … → {stops[-1]}"
        if width < 760 and len(stops) > 3:
            return f"{stops[0]} → {stops[1]} → … → {stops[-1]}"
        return " → ".join(stops)

    # ------------------------------------------------------------------
    # Canvas helpers
    # ------------------------------------------------------------------

    def _rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        self.create_polygon(points, smooth=True, **kwargs)

