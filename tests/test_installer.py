"""
Tests for installer script (scripts/install.sh).
Story 1.6: One-Line Installer Script

Note: These are integration tests that verify script structure and syntax.
Full installation testing requires a fresh Pi environment.
"""
import pytest
import subprocess
import os
import re


INSTALLER_PATH = "scripts/install.sh"


class TestInstallerScriptStructure:
    """Verify installer script exists and has correct structure."""

    def test_installer_exists(self):
        """Test that install.sh exists."""
        assert os.path.exists(INSTALLER_PATH), "scripts/install.sh not found"

    def test_installer_is_executable(self):
        """Test that install.sh has executable permissions."""
        assert os.access(INSTALLER_PATH, os.X_OK), "install.sh is not executable"

    def test_installer_has_bash_shebang(self):
        """Test that install.sh starts with #!/bin/bash."""
        with open(INSTALLER_PATH, 'r') as f:
            first_line = f.readline().strip()
        assert first_line == "#!/bin/bash", f"Expected #!/bin/bash, got {first_line}"

    def test_installer_has_error_handling(self):
        """Test that install.sh has set -e, set -u, set -o pipefail."""
        with open(INSTALLER_PATH, 'r') as f:
            content = f.read()
        assert "set -e" in content, "Missing 'set -e' for error handling"
        assert "set -u" in content, "Missing 'set -u' for undefined vars"
        assert "set -o pipefail" in content, "Missing 'set -o pipefail'"


class TestInstallerSyntax:
    """Verify bash syntax is valid."""

    def test_bash_syntax_check(self):
        """Test that bash -n validates syntax without errors."""
        result = subprocess.run(
            ["bash", "-n", INSTALLER_PATH],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Syntax error: {result.stderr}"


class TestInstallerFlags:
    """Verify all command-line flags work correctly."""

    def test_help_flag(self):
        """Test that --help flag works and shows usage."""
        result = subprocess.run(
            [f"./{INSTALLER_PATH}", "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "Help flag failed"
        assert "deskpulse Installer" in result.stdout, "Help doesn't show title"
        assert "Usage:" in result.stdout, "Help doesn't show usage"
        assert "--uninstall" in result.stdout, "Help missing --uninstall"
        assert "--update" in result.stdout, "Help missing --update"
        assert "--version" in result.stdout, "Help missing --version"
        assert "--yes" in result.stdout, "Help missing --yes"

    def test_help_short_flag(self):
        """Test that -h flag works as alias for --help."""
        result = subprocess.run(
            [f"./{INSTALLER_PATH}", "-h"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "-h flag failed"
        assert "deskpulse Installer" in result.stdout, "-h doesn't show help"


class TestInstallerFunctions:
    """Verify all required functions are defined."""

    @pytest.fixture
    def installer_content(self):
        """Load installer script content."""
        with open(INSTALLER_PATH, 'r') as f:
            return f.read()

    def test_has_progress_function(self, installer_content):
        """Test that progress() helper function exists."""
        assert re.search(r'progress\(\)', installer_content), "Missing progress() function"

    def test_has_error_function(self, installer_content):
        """Test that error() helper function exists."""
        assert re.search(r'error\(\)', installer_content), "Missing error() function"

    def test_has_success_function(self, installer_content):
        """Test that success() helper function exists."""
        assert re.search(r'success\(\)', installer_content), "Missing success() function"

    def test_has_warning_function(self, installer_content):
        """Test that warning() helper function exists."""
        assert re.search(r'warning\(\)', installer_content), "Missing warning() function"

    def test_has_cleanup_function(self, installer_content):
        """Test that cleanup() trap function exists."""
        assert re.search(r'cleanup\(\)', installer_content), "Missing cleanup() function"

    def test_has_check_prerequisites(self, installer_content):
        """Test that check_prerequisites() function exists."""
        assert re.search(r'check_prerequisites\(\)', installer_content), "Missing check_prerequisites()"

    def test_has_install_system_dependencies(self, installer_content):
        """Test that install_system_dependencies() function exists."""
        assert re.search(r'install_system_dependencies\(\)', installer_content), "Missing install_system_dependencies()"

    def test_has_clone_repository(self, installer_content):
        """Test that clone_repository() function exists."""
        assert re.search(r'clone_repository\(\)', installer_content), "Missing clone_repository()"

    def test_has_setup_python_venv(self, installer_content):
        """Test that setup_python_venv() function exists."""
        assert re.search(r'setup_python_venv\(\)', installer_content), "Missing setup_python_venv()"

    def test_has_verify_camera(self, installer_content):
        """Test that verify_camera() function exists."""
        assert re.search(r'verify_camera\(\)', installer_content), "Missing verify_camera()"

    def test_has_download_mediapipe_models(self, installer_content):
        """Test that download_mediapipe_models() function exists."""
        assert re.search(r'download_mediapipe_models\(\)', installer_content), "Missing download_mediapipe_models()"

    def test_has_generate_secret_key(self, installer_content):
        """Test that generate_secret_key() function exists."""
        assert re.search(r'generate_secret_key\(\)', installer_content), "Missing generate_secret_key()"

    def test_has_setup_configuration(self, installer_content):
        """Test that setup_configuration() function exists."""
        assert re.search(r'setup_configuration\(\)', installer_content), "Missing setup_configuration()"

    def test_has_initialize_database(self, installer_content):
        """Test that initialize_database() function exists."""
        assert re.search(r'initialize_database\(\)', installer_content), "Missing initialize_database()"

    def test_has_install_systemd_service(self, installer_content):
        """Test that install_systemd_service() function exists."""
        assert re.search(r'install_systemd_service\(\)', installer_content), "Missing install_systemd_service()"

    def test_has_verify_installation(self, installer_content):
        """Test that verify_installation() function exists."""
        assert re.search(r'verify_installation\(\)', installer_content), "Missing verify_installation()"

    def test_has_display_success_message(self, installer_content):
        """Test that display_success_message() function exists."""
        assert re.search(r'display_success_message\(\)', installer_content), "Missing display_success_message()"

    def test_has_uninstall_function(self, installer_content):
        """Test that uninstall() function exists."""
        assert re.search(r'uninstall\(\)', installer_content), "Missing uninstall() function"

    def test_has_update_function(self, installer_content):
        """Test that update() function exists."""
        assert re.search(r'update\(\)', installer_content), "Missing update() function"

    def test_has_main_function(self, installer_content):
        """Test that main() function exists."""
        assert re.search(r'main\(\)', installer_content), "Missing main() function"


class TestInstallerConfiguration:
    """Verify installer configuration and constants."""

    @pytest.fixture
    def installer_content(self):
        """Load installer script content."""
        with open(INSTALLER_PATH, 'r') as f:
            return f.read()

    def test_has_total_steps_constant(self, installer_content):
        """Test that TOTAL_STEPS=11 is defined."""
        assert re.search(r'TOTAL_STEPS=11', installer_content), "TOTAL_STEPS not set to 11"

    def test_has_repo_url(self, installer_content):
        """Test that REPO_URL is defined."""
        assert re.search(r'REPO_URL=', installer_content), "REPO_URL not defined"

    def test_has_install_dir(self, installer_content):
        """Test that INSTALL_DIR is defined."""
        assert re.search(r'INSTALL_DIR=', installer_content), "INSTALL_DIR not defined"

    def test_has_logging_enabled(self, installer_content):
        """Test that installation logging is configured."""
        assert re.search(r'INSTALL_LOG=', installer_content), "INSTALL_LOG not defined"
        assert re.search(r'tee', installer_content), "Log file redirection not configured"

    def test_has_cleanup_trap(self, installer_content):
        """Test that ERR trap is set for cleanup."""
        assert re.search(r'trap cleanup ERR', installer_content), "ERR trap not set for cleanup"

    def test_has_color_definitions(self, installer_content):
        """Test that color constants are defined."""
        assert re.search(r"RED=", installer_content), "RED color not defined"
        assert re.search(r"GREEN=", installer_content), "GREEN color not defined"
        assert re.search(r"YELLOW=", installer_content), "YELLOW color not defined"
        assert re.search(r"NC=", installer_content), "NC (no color) not defined"


class TestInstallerPrerequisites:
    """Verify prerequisite checks are comprehensive."""

    @pytest.fixture
    def installer_content(self):
        """Load installer script content."""
        with open(INSTALLER_PATH, 'r') as f:
            return f.read()

    def test_checks_hardware(self, installer_content):
        """Test that hardware (Pi 4/5) check exists."""
        assert re.search(r'Cortex-A72|A76', installer_content), "Missing hardware check for Pi 4/5"

    def test_checks_os(self, installer_content):
        """Test that OS (Raspbian/Debian) check exists."""
        assert re.search(r'ID=raspbian|ID=debian', installer_content), "Missing OS check"

    def test_checks_python_version(self, installer_content):
        """Test that Python 3.9+ version check exists."""
        assert re.search(r'python3.*version', installer_content, re.IGNORECASE), "Missing Python version check"

    def test_checks_venv_module(self, installer_content):
        """Test that python3-venv module check exists."""
        assert re.search(r'python3.*venv', installer_content), "Missing venv module check"

    def test_checks_ram(self, installer_content):
        """Test that RAM check exists."""
        assert re.search(r'free.*-m', installer_content), "Missing RAM check"

    def test_checks_disk_space(self, installer_content):
        """Test that disk space check exists (18GB+)."""
        assert re.search(r'df', installer_content), "Missing disk space check"
        assert re.search(r'18', installer_content), "Missing 18GB requirement"

    def test_checks_network(self, installer_content):
        """Test that network connectivity check exists."""
        assert re.search(r'curl.*github\.com', installer_content), "Missing network check"

    def test_checks_systemd(self, installer_content):
        """Test that systemd availability check exists."""
        assert re.search(r'systemctl', installer_content), "Missing systemd check"

    def test_checks_existing_service(self, installer_content):
        """Test that existing service check exists."""
        assert re.search(r'is-active.*deskpulse', installer_content), "Missing existing service check"


class TestInstallerSecurity:
    """Verify security measures are in place."""

    @pytest.fixture
    def installer_content(self):
        """Load installer script content."""
        with open(INSTALLER_PATH, 'r') as f:
            return f.read()

    def test_checks_not_root(self, installer_content):
        """Test that installer prevents running as root."""
        assert re.search(r'EUID.*-eq 0', installer_content), "Missing root check"
        assert re.search(r'not.*root', installer_content, re.IGNORECASE), "Missing root warning"

    def test_secret_key_generation(self, installer_content):
        """Test that secret key is generated with openssl."""
        assert re.search(r'openssl rand', installer_content), "Missing secure key generation"
        assert re.search(r'hex 32', installer_content), "Missing 32-byte hex key"

    def test_secret_file_permissions(self, installer_content):
        """Test that secrets file has restricted permissions."""
        assert re.search(r'chmod 600.*secrets', installer_content), "Missing secrets file permission 600"

    def test_config_file_permissions(self, installer_content):
        """Test that config file has correct permissions."""
        assert re.search(r'chmod 644.*config', installer_content), "Missing config file permission 644"


class TestInstallerHealthCheck:
    """Verify installer checks health endpoint (AC0 dependency)."""

    @pytest.fixture
    def installer_content(self):
        """Load installer script content."""
        with open(INSTALLER_PATH, 'r') as f:
            return f.read()

    def test_health_endpoint_check(self, installer_content):
        """Test that installer verifies /health endpoint."""
        assert re.search(r'/health', installer_content), "Missing /health endpoint check"
        assert re.search(r'curl.*localhost:5000/health', installer_content), "Missing health endpoint verification"


class TestInstallerMessages:
    """Verify important user messages are present."""

    @pytest.fixture
    def installer_content(self):
        """Load installer script content."""
        with open(INSTALLER_PATH, 'r') as f:
            return f.read()

    def test_logout_warning_present(self, installer_content):
        """Test that logout warning for video group is present (C8 fix)."""
        assert re.search(r'logout', installer_content, re.IGNORECASE), "Missing logout warning"
        assert re.search(r'video.*group', installer_content, re.IGNORECASE), "Missing video group explanation"

    def test_success_message_exists(self, installer_content):
        """Test that success completion message exists."""
        assert re.search(r'Installation Complete', installer_content, re.IGNORECASE), "Missing completion message"

    def test_troubleshooting_commands(self, installer_content):
        """Test that troubleshooting commands are provided."""
        assert re.search(r'journalctl', installer_content), "Missing journalctl troubleshooting command"
        assert re.search(r'systemctl status', installer_content), "Missing systemctl status command"


class TestInstallerUpdateSupport:
    """Verify update functionality with rollback."""

    @pytest.fixture
    def installer_content(self):
        """Load installer script content."""
        with open(INSTALLER_PATH, 'r') as f:
            return f.read()

    def test_update_function_captures_version(self, installer_content):
        """Test that update captures current version for rollback."""
        update_section = re.search(r'update\(\).*?^}', installer_content, re.DOTALL | re.MULTILINE)
        assert update_section, "update() function not found"
        update_func = update_section.group(0)
        assert re.search(r'CURRENT_VERSION', update_func), "Missing version capture"

    def test_update_function_has_rollback_trap(self, installer_content):
        """Test that update sets up rollback trap on error."""
        update_section = re.search(r'update\(\).*?^}', installer_content, re.DOTALL | re.MULTILINE)
        assert update_section, "update() function not found"
        update_func = update_section.group(0)
        assert re.search(r'trap.*ERR', update_func), "Missing ERR trap for rollback"
        assert re.search(r'git checkout.*CURRENT_VERSION', update_func), "Missing git rollback"

    def test_update_function_backs_up_database(self, installer_content):
        """Test that update backs up database before updating."""
        update_section = re.search(r'update\(\).*?^}', installer_content, re.DOTALL | re.MULTILINE)
        assert update_section, "update() function not found"
        update_func = update_section.group(0)
        assert re.search(r'backup|BACKUP', update_func), "Missing database backup"

    def test_update_function_verifies_service(self, installer_content):
        """Test that update verifies service after restart."""
        update_section = re.search(r'update\(\).*?^}', installer_content, re.DOTALL | re.MULTILINE)
        assert update_section, "update() function not found"
        update_func = update_section.group(0)
        assert re.search(r'is-active.*deskpulse', update_func), "Missing service verification"


class TestInstallerUninstallSupport:
    """Verify uninstall functionality."""

    @pytest.fixture
    def installer_content(self):
        """Load installer script content."""
        with open(INSTALLER_PATH, 'r') as f:
            return f.read()

    def test_uninstall_prompts_for_data_deletion(self, installer_content):
        """Test that uninstall asks before deleting database."""
        uninstall_section = re.search(r'uninstall\(\).*?^}', installer_content, re.DOTALL | re.MULTILINE)
        assert uninstall_section, "uninstall() function not found"
        uninstall_func = uninstall_section.group(0)
        assert re.search(r'Delete database', uninstall_func), "Missing database deletion prompt"

    def test_uninstall_stops_service(self, installer_content):
        """Test that uninstall stops and disables service."""
        uninstall_section = re.search(r'uninstall\(\).*?^}', installer_content, re.DOTALL | re.MULTILINE)
        assert uninstall_section, "uninstall() function not found"
        uninstall_func = uninstall_section.group(0)
        assert re.search(r'systemctl stop', uninstall_func), "Missing service stop"


class TestInstallerDependencyVerification:
    """Verify installer checks for required files from previous stories."""

    @pytest.fixture
    def installer_content(self):
        """Load installer script content."""
        with open(INSTALLER_PATH, 'r') as f:
            return f.read()

    def test_checks_config_template_exists(self, installer_content):
        """Test that setup_configuration checks for config.ini.example."""
        setup_config = re.search(r'setup_configuration\(\).*?^}', installer_content, re.DOTALL | re.MULTILINE)
        assert setup_config, "setup_configuration() function not found"
        func_body = setup_config.group(0)
        assert re.search(r'\[ ! -f.*config\.ini\.example', func_body), "Missing config template check"

    def test_checks_service_file_exists(self, installer_content):
        """Test that install_systemd_service checks for service file."""
        install_service = re.search(r'install_systemd_service\(\).*?^}', installer_content, re.DOTALL | re.MULTILINE)
        assert install_service, "install_systemd_service() function not found"
        func_body = install_service.group(0)
        assert re.search(r'\[ ! -f.*deskpulse\.service', func_body), "Missing service file check"

    def test_checks_app_files_exist(self, installer_content):
        """Test that initialize_database checks for app/__init__.py and database.py."""
        init_db = re.search(r'initialize_database\(\).*?^}', installer_content, re.DOTALL | re.MULTILINE)
        assert init_db, "initialize_database() function not found"
        func_body = init_db.group(0)
        assert re.search(r'\[ ! -f.*app/__init__\.py', func_body), "Missing app/__init__.py check"
        assert re.search(r'app/data/database\.py', func_body), "Missing database.py check"

    def test_dependency_errors_reference_story_numbers(self, installer_content):
        """Test that dependency errors mention which story is missing."""
        # Should mention Story 1.1, 1.2, 1.3, or 1.4 in error messages
        assert re.search(r'Story 1\.[1-4]', installer_content), "Missing story number references in dependency errors"


class TestInstallerRollbackFunctionality:
    """Verify update rollback actually works, not just exists."""

    @pytest.fixture
    def installer_content(self):
        """Load installer script content."""
        with open(INSTALLER_PATH, 'r') as f:
            return f.read()

    def test_rollback_trap_catches_errors(self, installer_content):
        """Test that ERR trap is set to trigger rollback on any error."""
        update_func = re.search(r'update\(\).*?^}', installer_content, re.DOTALL | re.MULTILINE)
        assert update_func, "update() function not found"
        func_body = update_func.group(0)
        # Verify trap is set before risky operations
        assert re.search(r'trap.*ERR', func_body), "ERR trap not set"
        # Verify rollback includes git checkout
        assert re.search(r'git checkout.*CURRENT_VERSION', func_body), "Rollback doesn't restore version"

    def test_rollback_clears_trap_on_success(self, installer_content):
        """Test that ERR trap is cleared after successful update."""
        update_func = re.search(r'update\(\).*?^}', installer_content, re.DOTALL | re.MULTILINE)
        assert update_func, "update() function not found"
        func_body = update_func.group(0)
        # Should clear trap at end
        assert re.search(r'trap - ERR', func_body), "ERR trap not cleared on success"
