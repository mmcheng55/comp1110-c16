"""
main.py
-------
Application entry point.

Creates the root Tkinter window (``App``), wires it up to the singleton
``Navigator``, and starts the Tkinter event loop.
"""

import tkinter as tk
from views.navigator import get_navigator


class App(tk.Tk):
    """Root application window.

    Subclasses :class:`tk.Tk` so the window itself is the Tkinter root.
    On construction it retrieves the global :class:`~views.navigator.Navigator`
    singleton and registers itself, which causes all views to be instantiated
    and the default view to be raised.
    """

    def __init__(self):
        super().__init__()

        # Configure the main window
        self.title("My Tkinter Application")
        self.geometry("600x400")
        self.minsize(400, 300)

        self.navigator = get_navigator()
        self.navigator.register_app(self)


def main():
    """Instantiate and run the application."""
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
