"""
base_view.py
------------
Provides the base class for all UI views in the application.
"""
import tkinter as tk

class BaseView(tk.Frame):
    """The base Tkinter frame from which all page views inherit.

    Provides common access to the :class:`~views.navigator.Navigator` instance
    so that views can switch pages or access the central app context.

    Parameters
    ----------
    parent : tk.Widget
        The parent widget.
    *args, **kwargs
        Forwarded to the underlying `tk.Frame`.
    """
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        from .navigator import Navigator, get_navigator

        self.navigator: Navigator = get_navigator()
