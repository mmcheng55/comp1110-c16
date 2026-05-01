"""
navigator.py
------------
View navigation and management for the Tkinter application.

Defines the :class:`Navigator` which controls the stack of UI frames (views)
and allows transitioning between them.
"""
import tkinter as tk

from .route_ranking_page import RouteRankingPage
from .routing_page import RoutingPage

class Navigator:
    """Manages view instantiation and transitions.

    Initializes the specified views and keeps them in a dictionary.
    Only the "current" view is raised to the top of the stack.

    Parameters
    ----------
    views_config : dict[str, type]
        A mapping from view name to the view class (e.g. `RoutingPage`).
    default_view : str
        The name of the view to display by default upon app startup.
    """
    def __init__(self, views_config, default_view):
        self.views_config = views_config
        self.instances = {}
        self.default_view_name = default_view
        self.current_view_name = default_view
        self.app: tk.Tk = None

    def register_app(self, app):
        """Register the main application window and instantiate all views.

        Parameters
        ----------
        app : tk.Tk
            The root Tk application window where frames will be gridded.
        """
        self.app = app
        
        # Instantiate all views and stack them
        for name, ViewClass in self.views_config.items():
            instance = ViewClass(app)
            instance.grid(row=0, column=0, sticky="nsew")
            self.instances[name] = instance
            
        app.grid_rowconfigure(0, weight=1)
        app.grid_columnconfigure(0, weight=1)
        
        self.navigate_to(self.default_view_name)

    def navigate_to(self, view_name):
        """Switch to a specific view by name.

        Raises the requested view to the top of the widget stack so it becomes
        visible.

        Parameters
        ----------
        view_name : str
            The identifier of the view to switch to.
        """
        if view_name in self.instances:
            self.current_view_name = view_name
            instance = self.instances[view_name]
            instance.tkraise()
        else:
            print(f"View '{view_name}' not found.")

navigator = None
views: dict[str, tk.Frame] = {
    "home": RoutingPage,
    "ranking": RouteRankingPage,
}
default_view = "home"

def get_navigator():
    """Retrieve the singleton instance of the Navigator.

    Returns
    -------
    Navigator
        The globally shared navigator instance.
    """
    global navigator
    if navigator is None:
        navigator = Navigator(views, default_view=default_view)
    return navigator
