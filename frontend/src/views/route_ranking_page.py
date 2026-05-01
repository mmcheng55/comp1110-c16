"""
route_ranking_page.py
---------------------
Page for displaying ranked route results.
"""
import tkinter as tk
from tkinter import messagebox, ttk
import re

from models import Route
from .base_view import BaseView
from .components import RouteCard

FONT = ("Helvetica", 14)

SCORING_LABELS = {
    "1": "Cheapest",
    "2": "Fastest",
    "3": "Most Scenic",
    "4": "Balanced",
}

class RouteRankingPage(BaseView):
    """The view that displays a list of computed routes.

    Shows RouteCard components in a scrollable list and provides a button
    to return to the routing form.
    """
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.routes: list[Route] = []

        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas, padding=20)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.top_bar = ttk.Frame(self.scrollable_frame)
        self.top_bar.pack(fill="x", pady=(0, 8))
        self.back_button = ttk.Button(self.top_bar, text="Return", command=self._return_home)
        self.back_button.pack(side="left")

        self.title_frame = ttk.Frame(self.scrollable_frame)
        self.title_frame.pack(fill="x", pady=(10, 20))
        self.title_label = ttk.Label(
            self.title_frame,
            text="Best Routes for You",
            font=FONT,
            anchor="center",
            justify="center",
        )
        self.title_label.pack(fill="x")

        self.card_container = ttk.Frame(self.scrollable_frame)
        self.card_container.pack(fill="both", expand=True, pady=(12, 0))

        self._show_empty_state()

    def _on_canvas_resize(self, event):
        self.canvas.itemconfigure(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _show_empty_state(self):
        for widget in self.card_container.winfo_children():
            widget.destroy()
        ttk.Label(
            self.card_container,
            text="No routes found for this trip.",
            font=FONT,
            anchor="center",
        ).pack(fill="x", pady=20)

    def load_routes(self, routes: list[Route], sort_choice: str, start: str, finish: str):
        self.routes = routes[:3]
        preference_text = SCORING_LABELS.get(sort_choice, "Balanced")
        self.title_label.configure(text=f"Best Routes from {start} to {finish}\nRanked by score ({preference_text})")
        for widget in self.card_container.winfo_children():
            widget.destroy()

        if not self.routes:
            self._show_empty_state()
            return

        for index, route in enumerate(self.routes):
            rank = route.rank if route.rank is not None else index + 1
            description = self._get_interchange_stops(route, start, finish)
            transfer_summary = self._format_transfer_summary(route)
            lines = self._extract_lines(route)
            card = RouteCard(
                self.card_container,
                rank=rank,
                description=description,
                total_cost=route.total_cost,
                total_distance_km=route.total_distance_km,
                travel_time_minutes=route.travel_time_minutes,
                transfer_count=route.transfer_count,
                score=route.score,
                transfer_summary=transfer_summary,
                lines=lines,
                on_select=lambda i=index: self.on_route_selected(i),
            )
            card.pack(fill="x", pady=8)

    def on_route_selected(self, route_index: int):
        if route_index < 0 or route_index >= len(self.routes):
            messagebox.showerror("Route error", "The selected route could not be opened.")
            return

        route = self.routes[route_index]
        details_window = tk.Toplevel(self)
        details_window.title(f"Route #{route.rank or route_index + 1} Details")
        details_window.geometry("640x420")
        details_window.minsize(520, 320)

        container = ttk.Frame(details_window, padding=16)
        container.pack(fill="both", expand=True)

        ttk.Label(
            container,
            text=route.description or "Route details",
            font=("Helvetica", 14, "bold"),
            wraplength=580,
            justify="left",
        ).pack(anchor="w", pady=(0, 12))

        summary_lines = [
            f"Fare: {self._format_money(route.total_cost)}",
            f"Time: {self._format_minutes(route.travel_time_minutes)}",
            f"Distance: {self._format_distance(route.total_distance_km)}",
            f"Transfers: {self._format_transfer_count(route.transfer_count)}",
            f"Score: {self._format_score(route.score)}",
        ]
        ttk.Label(container, text="\n".join(summary_lines), justify="left").pack(anchor="w", pady=(0, 12))

        detail_text = tk.Text(container, wrap="word", height=14)
        detail_text.pack(fill="both", expand=True)
        detail_text.insert("1.0", self._build_route_detail_text(route))
        detail_text.configure(state="disabled")

    @staticmethod
    def _format_money(value: float | None) -> str:
        return "N/A" if value is None else f"${value:.2f}"

    @staticmethod
    def _format_minutes(value: float | None) -> str:
        if value is None:
            return "Unavailable"
        if value < 60:
            return f"{value:.0f} min"
        hours = int(value // 60)
        minutes = int(value % 60)
        return f"{hours}h {minutes}m" if minutes else f"{hours}h"

    @staticmethod
    def _format_distance(value: float | None) -> str:
        return "N/A" if value is None else f"{value:.1f} km"

    @staticmethod
    def _format_transfer_count(value: int | None) -> str:
        return "N/A" if value is None else str(value)

    @staticmethod
    def _format_score(value: float | None) -> str:
        return "N/A" if value is None else f"{value:.2f}"

    def _build_route_detail_text(self, route: Route) -> str:
        payload = route.raw_payload or {}
        segments = payload.get("segments") if isinstance(payload.get("segments"), list) else []
        if segments:
            lines = ["Segments:"]
            for index, segment in enumerate(segments, start=1):
                if not isinstance(segment, dict):
                    continue
                properties = segment.get("segmentProperties") or segment.get("segmentPropertiesStruct") or {}
                from_stop = segment.get("from") or segment.get("fromStop") or segment.get("fromStopClass") or {}
                to_stop = segment.get("to") or segment.get("toStop") or segment.get("toStopClass") or {}
                from_name = from_stop.get("stopName") if isinstance(from_stop, dict) else "Unknown"
                to_name = to_stop.get("stopName") if isinstance(to_stop, dict) else "Unknown"
                mode = segment.get("type") or segment.get("segmentTransportationType")
                if mode is None and isinstance(properties, dict):
                    mode = properties.get("segmentTransportationType") or properties.get("type")
                fare = segment.get("fare")
                if fare is None and isinstance(properties, dict):
                    fare = properties.get("fareDollars")
                time = segment.get("time")
                if time is None and isinstance(properties, dict):
                    time = properties.get("time")
                parsed_time = self._coerce_float(time)
                if parsed_time is not None and parsed_time <= 0:
                    parsed_time = None
                score = segment.get("scenic")
                if score is None and isinstance(properties, dict):
                    score = properties.get("scenicIndex")

                lines.append(
                    f"{index}. {self._format_stop_name(str(from_name))} -> {self._format_stop_name(str(to_name))} | "
                    f"Mode: {mode or 'Unknown'} | Fare: {self._format_money(self._coerce_float(fare))} | "
                    f"Time: {self._format_minutes(parsed_time)} | "
                    f"Score: {self._format_score(self._coerce_float(score))}"
                )
            return "\n".join(lines)

        stop_path = payload.get("stopPath") if isinstance(payload.get("stopPath"), list) else []
        modes = payload.get("transportModes") if isinstance(payload.get("transportModes"), list) else []
        if not modes:
            modes = payload.get("modes") if isinstance(payload.get("modes"), list) else []
        if stop_path:
            lines = ["Path:"]
            for index, stop_name in enumerate(stop_path):
                mode_text = ""
                if 0 < index <= len(modes):
                    mode_text = f" ({modes[index - 1]})"
                lines.append(f"{index + 1}. {self._format_stop_name(str(stop_name))}{mode_text}")
            return "\n".join(lines)

        return "Detailed route information is not available for this route."

    @staticmethod
    def _format_stop_name(stop_name: str) -> str:
        words = re.findall(r"[A-Z]+(?=$|[A-Z][a-z])|[A-Z]?[a-z]+", stop_name)
        return " ".join(words) if words else stop_name

    @staticmethod
    def _coerce_float(value):
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _return_home(self):
        self.navigator.navigate_to("home")

    def _get_interchange_stops(self, route: Route, start: str, finish: str) -> str:
        payload = route.raw_payload or {}
        segments = payload.get("segments") if isinstance(payload.get("segments"), list) else []
        if not segments:
            return route.description or f"{start} -> {finish}"
        
        stops = []
        prev_line = None
        for i, seg in enumerate(segments):
            if not isinstance(seg, dict):
                continue
            line = seg.get("line") or seg.get("lineCode") or seg.get("routeName") or seg.get("route")
            
            from_stop = seg.get("from") or seg.get("fromStop") or {}
            from_name = from_stop.get("stopName") if isinstance(from_stop, dict) else str(from_stop)
            
            if i == 0:
                stops.append(from_name)
                prev_line = line
            elif line != prev_line:
                stops.append(from_name)
                prev_line = line
                
        last_seg = segments[-1]
        if isinstance(last_seg, dict):
            to_stop = last_seg.get("to") or last_seg.get("toStop") or {}
            to_name = to_stop.get("stopName") if isinstance(to_stop, dict) else str(to_stop)
            stops.append(to_name)
            
        clean_stops = []
        for s in stops:
            if not clean_stops or clean_stops[-1] != s:
                clean_stops.append(s)
                
        return " -> ".join(self._format_stop_name(str(s)) for s in clean_stops)

    @staticmethod
    def _extract_lines(route: Route) -> list[dict[str, str]]:
        """Return ordered unique line elements from route segments (interchange sequence)."""
        payload = route.raw_payload or {}
        segments = payload.get("segments") if isinstance(payload.get("segments"), list) else []
        seen_lines: list[dict[str, str]] = []
        prev_line: str | None = None
        for seg in segments:
            if not isinstance(seg, dict):
                continue
            line = (
                seg.get("line") or seg.get("lineCode")
                or seg.get("routeName") or seg.get("route")
            )
            mode = (
                seg.get("type") or seg.get("segmentTransportationType")
            )
            if mode is None and isinstance(seg.get("segmentProperties"), dict):
                mode = seg["segmentProperties"].get("segmentTransportationType") or seg["segmentProperties"].get("type")
            if not mode:
                mode = "Train" # Default fallback
                
            if line and str(line) != prev_line:
                seen_lines.append({"line": str(line), "mode": str(mode)})
                prev_line = str(line)
        return seen_lines

    @staticmethod
    def _format_transfer_summary(route: Route) -> str:
        payload = route.raw_payload or {}
        segments = payload.get("segments") if isinstance(payload.get("segments"), list) else []

        # Build interchange description from actual segment line data
        if segments:
            line_sequence: list[str] = []
            prev_line: str | None = None
            for seg in segments:
                if not isinstance(seg, dict):
                    continue
                line = (
                    seg.get("line") or seg.get("lineCode")
                    or seg.get("routeName") or seg.get("route")
                )
                if line and str(line) != prev_line:
                    line_sequence.append(str(line))
                    prev_line = str(line)
            if line_sequence:
                if len(line_sequence) == 1:
                    return f"Direct on {line_sequence[0]} line."
                return f"Interchange: {' → '.join(line_sequence)}"

        # Fallback to transport_modes
        modes = route.transport_modes or []
        cleaned_modes = [mode for i, mode in enumerate(modes) if i == 0 or mode != modes[i - 1]]
        if not cleaned_modes:
            return "Transfer details are not available for this route."
        if route.transfer_count in (None, 0):
            return f"Direct route via {cleaned_modes[0]}."
        return f"Transfer types: {' → '.join(cleaned_modes)}"