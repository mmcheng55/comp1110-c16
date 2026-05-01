"""
routing_page.py
---------------
The main home page for route planning.
"""
import tkinter as tk
from tkinter import messagebox, ttk
import re

from .base_view import BaseView
from .components import NetworkView
from controller import RouteController, NetworkController, NetworkCrawlController, FareController
from models import Stop

FONT = ("Helvetica", 14)

_GROUP_PREFIX = "── "


class RoutingPage(BaseView):
    """The home view containing the main routing form.

    Provides dropdowns for selecting the start and destination stops,
    and radio buttons for selecting the scoring preference.
    """
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        # Initialize the newly split controllers
        self.route_controller = RouteController(self.navigator)
        self.network_controller = NetworkController(self.navigator)
        self.mtr_controller = NetworkCrawlController(self.navigator)
        self.fare_controller = FareController(self.navigator)

        self.stop_lookup: dict[str, Stop] = {}
        self.all_stop_names: list[str] = []
        # Store the flat list including group headers so filtering can rebuild it
        self._grouped_values: list[str] = []

        self.pack(fill="both", expand=True)

        # Top menu buttons
        self.menu_button_row = ttk.Frame(self)
        self.menu_button_row.pack(pady=(20, 30))

        self.view_network_btn = ttk.Button(self.menu_button_row, text="View Network", command=self.show_network)
        self.view_network_btn.pack(side="left", padx=8)

        self.update_network_btn = ttk.Button(
            self.menu_button_row,
            text="Update Network",
            command=self.update_network_from_all,
        )
        self.update_network_btn.pack(side="left", padx=8)

        self.update_fares_btn = ttk.Button(
            self.menu_button_row,
            text="Update Fares",
            command=self.update_fares,
        )
        self.update_fares_btn.pack(side="left", padx=8)

        # Main form container
        self.form_container = ttk.Frame(self)
        self.form_container.pack()

        title_label = ttk.Label(self.form_container, text="Route", font=FONT)
        title_label.pack(pady=(0, 10))

        self.starting_stop_var = tk.StringVar()
        self.finishing_stop_var = tk.StringVar()
        self.radio_choice_var = tk.StringVar(value="1")

        start_frame = ttk.Frame(self.form_container)
        start_frame.pack(pady=10, fill="x")
        ttk.Label(start_frame, text="Your starting location:", font=FONT).pack(side="left")

        self.start_dropdown = ttk.Combobox(start_frame, textvariable=self.starting_stop_var, state="normal")
        self.start_dropdown.pack(side="right", expand=True, fill="x")

        finish_frame = ttk.Frame(self.form_container)
        finish_frame.pack(pady=10, fill="x")
        ttk.Label(finish_frame, text="Your destination:", font=FONT).pack(side="left")

        self.finish_dropdown = ttk.Combobox(finish_frame, textvariable=self.finishing_stop_var, state="normal")
        self.finish_dropdown.pack(side="right", expand=True, fill="x")

        # Bind filtering to both dropdowns
        self.start_dropdown.bind("<KeyRelease>", lambda e: self._filter_dropdown(e, self.start_dropdown))
        self.finish_dropdown.bind("<KeyRelease>", lambda e: self._filter_dropdown(e, self.finish_dropdown))

        # Prevent group-header entries from being selected via Up/Down keys
        self.start_dropdown.bind("<<ComboboxSelected>>", lambda e: self._reject_header(self.start_dropdown, self.starting_stop_var))
        self.finish_dropdown.bind("<<ComboboxSelected>>", lambda e: self._reject_header(self.finish_dropdown, self.finishing_stop_var))

        preference_label = ttk.Label(
            self.form_container,
            text="Choose how routes are scored:",
            font=FONT,
        )
        preference_label.pack(pady=(10, 0))

        radio_frame = ttk.Frame(self.form_container)
        radio_frame.pack(pady=15)
        ttk.Radiobutton(radio_frame, text="Cheapest", variable=self.radio_choice_var, value="1").pack(
            side="left", padx=10
        )
        ttk.Radiobutton(radio_frame, text="Fastest", variable=self.radio_choice_var, value="2").pack(
            side="left", padx=10
        )
        ttk.Radiobutton(radio_frame, text="Most Scenic", variable=self.radio_choice_var, value="3").pack(
            side="left", padx=10
        )
        ttk.Radiobutton(radio_frame, text="Balanced", variable=self.radio_choice_var, value="4").pack(
            side="left", padx=10
        )

        self.submit_btn = ttk.Button(self.form_container, text="Submit", command=self.on_submit)
        self.submit_btn.pack(pady=20)

        self.load_stop_options()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_header(value: str) -> bool:
        return value.startswith(_GROUP_PREFIX)

    def _reject_header(self, combobox: ttk.Combobox, var: tk.StringVar) -> None:
        """If the selected value is a group header, clear the entry."""
        if self._is_header(var.get()):
            var.set("")
            combobox.focus_set()

    def _build_grouped_values(self, line_to_stops: dict[str, list[Stop]]) -> list[str]:
        """Build a flat list with line-header entries followed by stop names."""
        result: list[str] = []
        for line, stops in line_to_stops.items():
            result.append(f"{_GROUP_PREFIX}{line}")
            for stop in stops:
                result.append(self._format_stop_name(stop.stop_name))
        return result

    def _filter_dropdown(self, event: tk.Event, combobox: ttk.Combobox) -> None:
        """Filter the dropdown list while the user types, then re-open it."""
        if event.keysym in (
            "Up", "Down", "Left", "Right", "Return", "Escape", "Tab",
            "Shift_L", "Shift_R", "Control_L", "Control_R",
            "Alt_L", "Alt_R", "Caps_Lock",
        ):
            return

        typed_text = combobox.get()
        cursor_pos = combobox.index(tk.INSERT)

        if not typed_text:
            combobox["values"] = self._grouped_values
        else:
            search_str = typed_text.lower()
            # Keep matching stops; drop headers that have no children left
            filtered: list[str] = []
            pending_header: str | None = None
            pending_added = False
            for entry in self._grouped_values:
                if self._is_header(entry):
                    # We'll add the header only if a following stop matches
                    pending_header = entry
                    pending_added = False
                elif search_str in entry.lower():
                    if pending_header and not pending_added:
                        filtered.append(pending_header)
                        pending_added = True
                    filtered.append(entry)
            combobox["values"] = filtered

        # Re-open the dropdown WITHOUT stealing focus from the entry widget.
        # We schedule the Post call via after() so it runs after the current
        # event is fully processed, which prevents focus from leaving the entry.
        def _post():
            try:
                combobox.tk.call("ttk::combobox::Post", combobox)
            except tk.TclError:
                pass
            # Restore cursor position
            combobox.icursor(cursor_pos)
            combobox.selection_clear()

        combobox.after(0, _post)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def load_stop_options(self) -> None:
        """Load stops grouped by line; fall back to a flat list if no line data."""
        line_to_stops = self.network_controller.get_stops_by_line()

        if line_to_stops:
            self._grouped_values = self._build_grouped_values(line_to_stops)
            # All selectable stop names (excluding headers)
            self.all_stop_names = [v for v in self._grouped_values if not self._is_header(v)]
        else:
            # Fallback: plain stop list without grouping
            stops = self.network_controller.get_stops()
            if not stops:
                return
            self.all_stop_names = [self._format_stop_name(stop.stop_name) for stop in stops]
            self._grouped_values = self.all_stop_names[:]

        # Rebuild lookup mapping formatted name -> Stop object
        all_stops = self.network_controller.get_stops()
        self.stop_lookup = {
            self._format_stop_name(stop.stop_name): stop for stop in all_stops
        }

        self.start_dropdown["values"] = self._grouped_values
        self.finish_dropdown["values"] = self._grouped_values

        if self.all_stop_names:
            self.starting_stop_var.set(self.all_stop_names[0])
            self.finishing_stop_var.set(
                self.all_stop_names[1] if len(self.all_stop_names) > 1 else self.all_stop_names[0]
            )

    @staticmethod
    def _format_stop_name(stop_name: str) -> str:
        words = re.findall(r"[A-Z]+(?=$|[A-Z][a-z])|[A-Z]?[a-z]+", stop_name)
        return " ".join(words) if words else stop_name

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def show_network(self):
        network_data = self.network_controller.get_network()
        if not network_data or not (network_data.get("stops") or network_data.get("segments")):
            from tkinter import messagebox
            messagebox.showinfo(
                "No Network Data",
                "No network data is available yet.\n\nUse 'Update Network' to load the transit network first.",
            )
            return
        NetworkView(self, network_data)

    def update_network_from_all(self):
        self.update_network_btn.configure(state="disabled")
        try:
            success, message = self.mtr_controller.import_network_from_all_crawlers()
            if success:
                self.load_stop_options()
                messagebox.showinfo("Network Updated", message)
            else:
                messagebox.showerror("Update Failed", message)
        finally:
            self.update_network_btn.configure(state="normal")

    def update_fares(self):
        """Action for Update Fares button"""
        from tkinter import messagebox
        import threading

        def task():
            try:
                self.fare_controller.update_fares_from_all()
                self.after(0, lambda: messagebox.showinfo(
                    "Fares Updated", "Fares have been updated successfully.", parent=self
                ))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror(
                    "Error", f"Failed to update fares: {e}", parent=self
                ))

        threading.Thread(target=task, daemon=True).start()

    def on_submit(self):
        start_name = self.starting_stop_var.get()
        finish_name = self.finishing_stop_var.get()
        sort_choice = self.radio_choice_var.get()

        # Reject group headers
        if self._is_header(start_name) or self._is_header(finish_name):
            messagebox.showerror(
                "Invalid selection",
                "Please select a station (not a line heading) for both fields.",
            )
            return

        if start_name == finish_name:
            messagebox.showerror(
                "Invalid route",
                "Your starting location and your destination must be different.",
            )
            return

        start_stop = self.stop_lookup.get(start_name)
        finish_stop = self.stop_lookup.get(finish_name)
        if start_stop is None or finish_stop is None:
            messagebox.showerror(
                "Missing stop",
                "Please select valid stops from the dropdown list for both your starting location and your destination.",
            )
            return

        self.submit_btn.config(state="disabled", text="Fetching...")
        self.update_idletasks()

        import threading

        def fetch_task():
            try:
                top_routes = self.route_controller.get_route(
                    start_stop, finish_stop, sort_choice=sort_choice, fare_controller=self.fare_controller
                )
                self.after(0, lambda: self._on_submit_complete(top_routes, sort_choice, start_name, finish_name))
            except Exception as e:
                self.after(0, lambda: self._on_submit_error(str(e)))

        threading.Thread(target=fetch_task, daemon=True).start()

    def _on_submit_complete(self, top_routes, sort_choice, start_name, finish_name):
        self.submit_btn.config(state="normal", text="Submit")
        if top_routes is None:
            messagebox.showerror(
                "Route Not Found",
                "No route could be found between the selected stops with the current settings.",
            )
            return

        ranking_view = self.navigator.instances.get("ranking")
        if ranking_view is None:
            messagebox.showerror(
                "Configuration Error",
                "Unable to open the ranking page because it is not registered with the navigator.",
            )
            return

        ranking_view.load_routes(top_routes, sort_choice, start_name, finish_name)
        self.navigator.navigate_to("ranking")

    def _on_submit_error(self, error_msg):
        self.submit_btn.config(state="normal", text="Submit")
        messagebox.showerror("Error", f"Failed to fetch route: {error_msg}")

    def view_will_appear(self):
        """Refresh view contents each time the view is shown."""
        self.load_stop_options()
        # Re-select current stops to update any changes in the stop list
        if self.starting_stop_var.get() in self.stop_lookup:
            self.starting_stop_var.set(self.starting_stop_var.get())
        if self.finishing_stop_var.get() in self.stop_lookup:
            self.finishing_stop_var.set(self.finishing_stop_var.get())
