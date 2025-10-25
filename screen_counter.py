import tkinter as tk
from pynput import mouse, keyboard
import sys
import ctypes
from typing import Optional, List, Tuple

# --- Configuration ---
# Aesthetics for the click markers
CIRCLE_RADIUS = 15
CIRCLE_COLOR = "red"
TEXT_COLOR = "#FEFEFE"
FONT_CONFIG = ("Consolas", 11, "bold")

# Aesthetics for the main counter display
COUNTER_FONT_CONFIG = ("Arial", 50, "bold")
COUNTER_BG_COLOR = "red"
COUNTER_FG_COLOR = "#FEFEFE"  # Use off-white to prevent being transparent

class ClickCounterApp:
    """
    A full-screen, transparent overlay application to count and mark mouse clicks.

    This optimized version uses canvas item tagging for efficient clearing
    and includes type hinting for improved readability and maintainability.
    """
    def __init__(self):
        self.count: int = 0
        # Stores (circle_id, text_id) for the undo functionality.
        self.drawn_items: List[Tuple[int, int]] = []
        
        self.keyboard_controller = keyboard.Controller()
        
        # This flag prevents the app from closing when we programmatically
        # press ESC after a right-click (to close potential context menus).
        self.suppress_esc: bool = False
        
        # --- UI Setup ---
        self.root = tk.Tk()
        self._setup_root_window()
        self._create_widgets()
        
         # --- Print Credit Logo to Console ---
        logo = """
        ---------------------------------
        --     Created By Jacky Chay   --
        ---------------------------------
        """
        print(logo)
    
        # --- Start Event Listeners ---
        # Listeners run in separate threads, so GUI updates must be scheduled.
        self.mouse_listener: Optional[mouse.Listener] = None
        self.keyboard_listener: Optional[keyboard.Listener] = None
        self._start_listeners()
        
        print("Click Counter Activated: \nL-Click: Count | R-Click: Undo | R: Reset | ESC: Quit")
        self.root.mainloop()

    def _setup_root_window(self) -> None:
        """Configure the main application window to be a transparent overlay."""
        self.root.title("Click Counter")
        self.root.overrideredirect(True)
        self.root.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0")
        self.root.attributes('-topmost', True)
        self.root.attributes('-transparentcolor', 'white')
        self.root.config(bg='white')
        
        # Ensure a clean shutdown if the window is closed by the OS
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)

    def _create_widgets(self) -> None:
        """Create and place the canvas and labels for the UI."""
        self.canvas = tk.Canvas(self.root, bg='white', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.counter_label = tk.Label(
            self.root, text="0", font=COUNTER_FONT_CONFIG, bg=COUNTER_BG_COLOR,
            fg=COUNTER_FG_COLOR, padx=10, pady=5
        )
        self.counter_label.place(x=20, y=20)

        instructions = "L-Click: Count | R-Click: Undo Last | R: Reset | ESC: Quit"
        self.info_label = tk.Label(
            self.root, text=instructions, font=("Arial", 10),
            bg=COUNTER_BG_COLOR, fg=COUNTER_FG_COLOR
        )
        self.info_label.place(relx=0.5, rely=0.98, anchor='center')

    def _start_listeners(self) -> None:
        """Initialize and start the pynput mouse and keyboard listeners."""
        self.mouse_listener = mouse.Listener(on_click=self.on_click)
        self.keyboard_listener = keyboard.Listener(on_press=self.on_press)
        self.mouse_listener.start()
        self.keyboard_listener.start()

    def on_click(self, x: int, y: int, button: mouse.Button, pressed: bool) -> None:
        """Callback for mouse click events from the pynput listener."""
        if not pressed:
            return

        # Use root.after to safely schedule GUI updates from this non-main thread.
        if button == mouse.Button.left:
            self.root.after(0, self.process_click, x, y)
        elif button == mouse.Button.right:
            self.root.after(0, self.undo_last_click)
            self.suppress_esc = True 
            self.keyboard_controller.tap(keyboard.Key.esc)

    def on_press(self, key) -> None:
        """Callback for key press events from the pynput listener."""
        # Handle special keys (non-character)
        if isinstance(key, keyboard.Key):
            if key == keyboard.Key.esc:
                if self.suppress_esc:
                    self.suppress_esc = False
                    return
                self.quit_app()
        # Handle character keys
        elif isinstance(key, keyboard.KeyCode):
            if key.char and key.char.lower() == 'r':
                self.root.after(0, self.reset_counter)

    def process_click(self, x: int, y: int) -> None:
        """Handles the logic for a left-click: increment, update, and draw."""
        self.count += 1
        self.update_counter_label()
        self.draw_marker(x, y)

    def draw_marker(self, x: int, y: int) -> None:
        """Draws a numbered circle, tagging it for efficient deletion."""
        x1, y1 = x - CIRCLE_RADIUS, y - CIRCLE_RADIUS
        x2, y2 = x + CIRCLE_RADIUS, y + CIRCLE_RADIUS
        
        # OPTIMIZATION: Tag items for easy bulk deletion.
        tag = "marker"
        circle_id = self.canvas.create_oval(x1, y1, x2, y2, fill=CIRCLE_COLOR, outline="", tags=tag)
        text_id = self.canvas.create_text(x, y, text=str(self.count), fill=TEXT_COLOR, font=FONT_CONFIG, tags=tag)
        
        self.drawn_items.append((circle_id, text_id))
        
    def update_counter_label(self) -> None:
        """Updates the text of the main counter label."""
        self.counter_label.config(text=str(self.count))

    def reset_counter(self) -> None:
        """Resets the count and clears all markers from the screen efficiently."""
        print("Counter and markers reset.")
        self.count = 0
        self.update_counter_label()
        
        # OPTIMIZATION: Delete all tagged items in one call. Far more efficient.
        self.canvas.delete("marker")
        self.drawn_items.clear()

    def undo_last_click(self) -> None:
        """Removes the last drawn marker and decrements the count."""
        if not self.drawn_items:
            return

        self.count -= 1
        self.update_counter_label()

        circle_id, text_id = self.drawn_items.pop()
        self.canvas.delete(circle_id)
        self.canvas.delete(text_id)

    def quit_app(self) -> None:
        """Stops listeners and gracefully exits the application."""
        print("Exiting counter.")
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        self.root.destroy()

def set_dpi_awareness() -> None:
    """On Windows, set DPI awareness to get accurate click coordinates."""
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception as e:
            print(f"Warning: Could not set DPI awareness. Clicks might be offset. Error: {e}")

if __name__ == "__main__":
    set_dpi_awareness()
    app = ClickCounterApp()