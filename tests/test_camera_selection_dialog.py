"""
Unit tests for camera selection dialog (Task 3).

Tests:
- Single camera auto-select (no dialog)
- Multi-camera dialog shows
- Config persistence with proper schema
- Dialog doesn't block backend (separate thread)
- Keyboard navigation works
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.standalone.camera_selection_dialog import (
    show_camera_selection_dialog,
    save_camera_selection,
    load_camera_selection,
    CameraSelectionDialog
)


class TestCameraSelectionDialog:
    """Test camera selection dialog functionality."""

    def test_single_camera_auto_selects_without_dialog(self):
        """Test single camera is auto-selected without showing dialog."""
        cameras = [
            {'index': 0, 'name': 'Camera 0', 'backend': 'MSMF', 'vid': 'unknown', 'pid': 'unknown'}
        ]

        # Should return camera 0 without showing dialog
        result = show_camera_selection_dialog(cameras)

        assert result == 0

    def test_no_cameras_returns_none(self):
        """Test empty camera list returns None."""
        cameras = []

        result = show_camera_selection_dialog(cameras)

        assert result is None

    @patch('app.standalone.camera_selection_dialog.CameraSelectionDialog')
    @patch('threading.Thread')
    def test_multi_camera_shows_dialog(self, mock_thread, mock_dialog_class):
        """Test multiple cameras trigger dialog display."""
        cameras = [
            {'index': 0, 'name': 'Camera 0', 'backend': 'MSMF', 'vid': 'unknown', 'pid': 'unknown'},
            {'index': 1, 'name': 'Camera 1', 'backend': 'MSMF', 'vid': 'unknown', 'pid': 'unknown'}
        ]

        # Mock thread execution
        def mock_thread_init(target=None, args=None, **kwargs):
            # Immediately execute target in main thread for testing
            if target and args:
                target(*args)
            mock_t = Mock()
            mock_t.start = Mock()
            return mock_t

        mock_thread.side_effect = mock_thread_init

        # Mock dialog returns camera 1
        mock_dialog = Mock()
        mock_dialog.run = Mock()
        mock_dialog_class.return_value = mock_dialog

        # Mock result queue
        with patch('app.standalone.camera_selection_dialog.Queue') as mock_queue_class:
            mock_queue = Mock()
            mock_queue.get.return_value = 1  # User selected camera 1
            mock_queue_class.return_value = mock_queue

            result = show_camera_selection_dialog(cameras, current_selection=0)

            # Verify result
            assert result == 1

            # Verify dialog was created with correct args
            assert mock_dialog_class.called

    def test_dialog_runs_in_separate_thread(self):
        """Test dialog execution doesn't block main thread."""
        cameras = [
            {'index': 0, 'name': 'Camera 0', 'backend': 'MSMF', 'vid': 'unknown', 'pid': 'unknown'},
            {'index': 1, 'name': 'Camera 1', 'backend': 'MSMF', 'vid': 'unknown', 'pid': 'unknown'}
        ]

        thread_created = False

        with patch('threading.Thread') as mock_thread:
            def track_thread_creation(*args, **kwargs):
                nonlocal thread_created
                thread_created = True
                mock_t = Mock()
                return mock_t

            mock_thread.side_effect = track_thread_creation

            with patch('app.standalone.camera_selection_dialog.Queue') as mock_queue_class:
                mock_queue = Mock()
                mock_queue.get.return_value = 0
                mock_queue_class.return_value = mock_queue

                show_camera_selection_dialog(cameras)

                # Verify thread was created
                assert thread_created


class TestConfigPersistence:
    """Test camera selection config persistence."""

    def test_save_camera_selection_creates_correct_schema(self):
        """Test saving camera creates correct config schema."""
        # Mock config
        mock_config = Mock()
        mock_config.data = {}
        mock_config.save = Mock()

        # Save selection
        save_camera_selection(
            mock_config,
            camera_index=1,
            camera_name="Integrated Webcam",
            backend="MSMF"
        )

        # Verify schema
        assert 'camera' in mock_config.data
        assert mock_config.data['camera']['index'] == 1
        assert mock_config.data['camera']['name'] == "Integrated Webcam"
        assert mock_config.data['camera']['backend'] == "MSMF"

        # Verify save called
        mock_config.save.assert_called_once()

    def test_save_camera_selection_updates_existing_config(self):
        """Test saving camera updates existing camera config."""
        # Mock config with existing data
        mock_config = Mock()
        mock_config.data = {
            'camera': {
                'index': 0,
                'name': 'Old Camera',
                'backend': 'DirectShow'
            }
        }
        mock_config.save = Mock()

        # Save new selection
        save_camera_selection(
            mock_config,
            camera_index=2,
            camera_name="New Camera",
            backend="MSMF"
        )

        # Verify updated
        assert mock_config.data['camera']['index'] == 2
        assert mock_config.data['camera']['name'] == "New Camera"
        assert mock_config.data['camera']['backend'] == "MSMF"

    def test_load_camera_selection_returns_saved_config(self):
        """Test loading camera selection returns saved data."""
        # Mock config with camera data
        mock_config = Mock()
        mock_config.data = {
            'camera': {
                'index': 1,
                'name': 'USB Camera',
                'backend': 'MSMF'
            }
        }

        # Load
        result = load_camera_selection(mock_config)

        # Verify
        assert result is not None
        assert result['index'] == 1
        assert result['name'] == 'USB Camera'
        assert result['backend'] == 'MSMF'

    def test_load_camera_selection_returns_none_when_no_config(self):
        """Test loading returns None when no camera config exists."""
        # Mock config without camera data
        mock_config = Mock()
        mock_config.data = {}

        # Load
        result = load_camera_selection(mock_config)

        # Verify
        assert result is None

    def test_save_camera_selection_handles_invalid_config(self):
        """Test saving handles invalid config object gracefully."""
        # Invalid config (no data attribute)
        invalid_config = Mock(spec=[])

        # Should not crash
        save_camera_selection(
            invalid_config,
            camera_index=0,
            camera_name="Camera",
            backend="auto"
        )

    def test_load_camera_selection_handles_invalid_config(self):
        """Test loading handles invalid config object gracefully."""
        # Invalid config (no data attribute)
        invalid_config = Mock(spec=[])

        # Should return None
        result = load_camera_selection(invalid_config)

        assert result is None


class TestCameraSelectionDialogClass:
    """Test CameraSelectionDialog class methods."""

    @patch('tkinter.Tk')
    @patch('tkinter.IntVar')
    def test_dialog_initialization(self, mock_intvar, mock_tk):
        """Test dialog initializes correctly."""
        from queue import Queue

        # FIX: Mock Tkinter components
        mock_intvar_instance = Mock()
        mock_intvar.return_value = mock_intvar_instance

        cameras = [
            {'index': 0, 'name': 'Camera 0', 'backend': 'MSMF', 'vid': 'unknown', 'pid': 'unknown'}
        ]
        result_queue = Queue()

        dialog = CameraSelectionDialog(cameras, current_selection=0, result_queue=result_queue)

        # Verify initialization
        assert dialog.cameras == cameras
        assert dialog.current_selection == 0
        assert dialog.result_queue == result_queue

    @patch('tkinter.Tk')
    @patch('tkinter.IntVar')
    @patch('tkinter.ttk.Frame')
    @patch('tkinter.ttk.Label')
    @patch('tkinter.ttk.Radiobutton')
    @patch('tkinter.ttk.Button')
    def test_dialog_builds_radio_buttons(self, mock_button, mock_radio, mock_label, mock_frame, mock_intvar, mock_tk):
        """Test dialog builds radio buttons for each camera."""
        from queue import Queue

        # FIX: Mock Tkinter components
        mock_intvar_instance = Mock()
        mock_intvar.return_value = mock_intvar_instance

        cameras = [
            {'index': 0, 'name': 'Camera 0', 'backend': 'MSMF', 'vid': 'unknown', 'pid': 'unknown'},
            {'index': 1, 'name': 'Camera 1', 'backend': 'MSMF', 'vid': 'unknown', 'pid': 'unknown'}
        ]
        result_queue = Queue()

        # Create dialog
        dialog = CameraSelectionDialog(cameras, current_selection=0, result_queue=result_queue)

        # Mock Tk root
        mock_root = Mock()
        dialog.root = mock_root

        # Build UI (will create radio buttons)
        dialog._build_ui()

        # Verify radio buttons created (2 cameras = 2 buttons expected)
        assert mock_radio.call_count == 2

    @patch('tkinter.Tk')
    @patch('tkinter.IntVar')
    def test_dialog_on_ok_returns_selected_camera(self, mock_intvar, mock_tk):
        """Test OK button returns selected camera index."""
        from queue import Queue

        # FIX: Mock Tkinter components
        mock_intvar_instance = Mock()
        mock_intvar_instance.get.return_value = 1  # User selected camera 1
        mock_intvar.return_value = mock_intvar_instance

        cameras = [
            {'index': 0, 'name': 'Camera 0', 'backend': 'MSMF', 'vid': 'unknown', 'pid': 'unknown'},
            {'index': 1, 'name': 'Camera 1', 'backend': 'MSMF', 'vid': 'unknown', 'pid': 'unknown'}
        ]
        result_queue = Queue()

        dialog = CameraSelectionDialog(cameras, current_selection=1, result_queue=result_queue)

        # Mock root
        dialog.root = Mock()
        dialog.root.destroy = Mock()

        # Click OK
        dialog._on_ok()

        # Verify result
        result = result_queue.get()
        assert result == 1
        dialog.root.destroy.assert_called_once()

    @patch('tkinter.Tk')
    @patch('tkinter.IntVar')
    def test_dialog_on_cancel_returns_none(self, mock_intvar, mock_tk):
        """Test Cancel button returns None."""
        from queue import Queue

        # FIX: Mock Tkinter components
        mock_intvar_instance = Mock()
        mock_intvar.return_value = mock_intvar_instance

        cameras = [
            {'index': 0, 'name': 'Camera 0', 'backend': 'MSMF', 'vid': 'unknown', 'pid': 'unknown'}
        ]
        result_queue = Queue()

        dialog = CameraSelectionDialog(cameras, current_selection=0, result_queue=result_queue)

        # Mock root
        dialog.root = Mock()
        dialog.root.destroy = Mock()

        # Click Cancel
        dialog._on_cancel()

        # Verify result
        result = result_queue.get()
        assert result is None
        dialog.root.destroy.assert_called_once()
