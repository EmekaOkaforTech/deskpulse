"""
Camera Selection Dialog using Tkinter.

Enterprise-grade camera selection UI with:
- Tkinter for BSD licensing (no LGPL concerns)
- Radio button selection
- OK/Cancel buttons
- Separate thread execution (doesn't block backend)
- Config persistence
- Single-camera auto-select
- Keyboard navigation (Tab, Enter, Esc)
"""

import tkinter as tk
from tkinter import ttk
import threading
import logging
from queue import Queue
from typing import List, Dict, Optional

logger = logging.getLogger('deskpulse.standalone.camera_selection')


def show_camera_selection_dialog(cameras: List[Dict[str, any]],
                                   current_selection: int = 0) -> Optional[int]:
    """
    Show camera selection dialog (blocking call).

    Args:
        cameras: List of camera dicts from detect_cameras_with_names()
        current_selection: Currently selected camera index (default)

    Returns:
        int: Selected camera index, or None if cancelled

    Single-camera systems return that camera without showing dialog.
    Multi-camera systems show radio button dialog.
    """
    if not cameras:
        logger.warning("No cameras provided to dialog")
        return None

    # Single camera: auto-select, no dialog
    if len(cameras) == 1:
        logger.info(f"Single camera detected, auto-selecting: {cameras[0]}")
        return cameras[0]['index']

    # Multiple cameras: show dialog
    logger.info(f"Showing camera selection dialog for {len(cameras)} cameras")

    # Result queue for thread communication
    result_queue = Queue()

    # Run dialog in separate thread
    dialog_thread = threading.Thread(
        target=_run_dialog_thread,
        args=(cameras, current_selection, result_queue),
        daemon=True
    )
    dialog_thread.start()

    # Wait for result (blocking)
    result = result_queue.get()

    logger.info(f"Camera selection result: {result}")
    return result


def _run_dialog_thread(cameras: List[Dict[str, any]],
                       current_selection: int,
                       result_queue: Queue):
    """
    Run dialog in background thread.

    Args:
        cameras: List of camera dicts
        current_selection: Current selection
        result_queue: Queue to return selected index
    """
    try:
        # Create and run dialog
        dialog = CameraSelectionDialog(cameras, current_selection, result_queue)
        dialog.run()

    except Exception as e:
        logger.exception(f"Dialog error: {e}")
        result_queue.put(None)


class CameraSelectionDialog:
    """
    Tkinter camera selection dialog.

    Features:
    - Radio buttons for each camera
    - OK/Cancel buttons
    - Keyboard navigation (Tab, Enter, Esc)
    - Modal dialog (blocks calling thread)
    - Clean BSD-licensed Tkinter (no Qt/LGPL)
    """

    def __init__(self, cameras: List[Dict[str, any]],
                 current_selection: int,
                 result_queue: Queue):
        """
        Initialize dialog.

        Args:
            cameras: List of camera dicts
            current_selection: Currently selected camera index
            result_queue: Queue to return result
        """
        self.cameras = cameras
        self.current_selection = current_selection
        self.result_queue = result_queue
        self.selected_index = tk.IntVar()
        self.root = None

    def run(self):
        """Run dialog (blocking)."""
        # Create root window
        self.root = tk.Tk()
        self.root.title("Select Camera - DeskPulse")
        self.root.resizable(False, False)

        # Set window size
        self.root.geometry("400x300")

        # Set default value
        self.selected_index.set(self.current_selection)

        # Build UI
        self._build_ui()

        # Keyboard bindings
        self.root.bind('<Return>', lambda e: self._on_ok())
        self.root.bind('<Escape>', lambda e: self._on_cancel())

        # Focus first radio button
        if hasattr(self, 'radio_buttons') and self.radio_buttons:
            self.radio_buttons[0].focus_set()

        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.root.winfo_height() // 2)
        self.root.geometry(f"+{x}+{y}")

        # Modal dialog
        self.root.grab_set()

        # Run event loop
        self.root.mainloop()

    def _build_ui(self):
        """Build dialog UI."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title label
        title_label = ttk.Label(
            main_frame,
            text="Choose a camera:",
            font=('TkDefaultFont', 10, 'bold')
        )
        title_label.pack(anchor=tk.W, pady=(0, 10))

        # Camera list frame
        camera_frame = ttk.Frame(main_frame)
        camera_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # Radio buttons for each camera
        self.radio_buttons = []
        for camera in self.cameras:
            # Format camera name
            index = camera['index']
            name = camera['name']
            label_text = f"{name} (index {index})"

            # Create radio button
            radio = ttk.Radiobutton(
                camera_frame,
                text=label_text,
                variable=self.selected_index,
                value=index
            )
            radio.pack(anchor=tk.W, pady=5)
            self.radio_buttons.append(radio)

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        # OK button
        ok_button = ttk.Button(
            button_frame,
            text="OK",
            command=self._on_ok,
            width=10
        )
        ok_button.pack(side=tk.LEFT, padx=(0, 10))

        # Cancel button
        cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
            width=10
        )
        cancel_button.pack(side=tk.LEFT)

    def _on_ok(self):
        """Handle OK button."""
        selected = self.selected_index.get()
        logger.info(f"Camera selected: {selected}")
        self.result_queue.put(selected)
        self.root.destroy()

    def _on_cancel(self):
        """Handle Cancel button."""
        logger.info("Camera selection cancelled")
        self.result_queue.put(None)
        self.root.destroy()


def save_camera_selection(config, camera_index: int, camera_name: str,
                           backend: str = "auto"):
    """
    Save camera selection to config.

    Args:
        config: Config object with save() method
        camera_index: Selected camera index
        camera_name: Camera name
        backend: Backend used (MSMF, DirectShow, auto)

    Schema: {'camera': {'index': 0, 'name': 'Camera 0', 'backend': 'auto'}}
    """
    if not hasattr(config, 'data'):
        logger.error("Invalid config object")
        return

    # Update config
    config.data.setdefault('camera', {})
    config.data['camera']['index'] = camera_index
    config.data['camera']['name'] = camera_name
    config.data['camera']['backend'] = backend

    # Save
    config.save()

    logger.info(f"Camera selection saved: index={camera_index}, "
               f"name={camera_name}, backend={backend}")


def load_camera_selection(config) -> Optional[Dict[str, any]]:
    """
    Load camera selection from config.

    Args:
        config: Config object with data attribute

    Returns:
        dict: {'index': int, 'name': str, 'backend': str} or None
    """
    if not hasattr(config, 'data'):
        logger.error("Invalid config object")
        return None

    camera_config = config.data.get('camera')

    if not camera_config:
        logger.info("No saved camera selection found")
        return None

    logger.info(f"Loaded camera selection: {camera_config}")
    return camera_config


if __name__ == '__main__':
    # Test dialog
    logging.basicConfig(level=logging.INFO)

    # Mock cameras
    test_cameras = [
        {'index': 0, 'name': 'Integrated Webcam', 'backend': 'MSMF', 'vid': '0x1234', 'pid': '0x5678'},
        {'index': 1, 'name': 'USB Camera', 'backend': 'MSMF', 'vid': '0xabcd', 'pid': '0xef01'},
        {'index': 2, 'name': 'Camera 2', 'backend': 'DirectShow', 'vid': 'unknown', 'pid': 'unknown'},
    ]

    print("Testing camera selection dialog...")
    print(f"Cameras: {len(test_cameras)}")

    result = show_camera_selection_dialog(test_cameras, current_selection=0)

    print(f"\nSelected camera: {result}")
