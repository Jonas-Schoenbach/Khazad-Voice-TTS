# Imports

# > Standard Library
import argparse
import os
from pathlib import Path

# Force AI models to download into the user data directory
from .config.ConfigManager import ConfigManager

# > Local Dependencies
from .engine_startup import EngineStartup

class KhazadCLI:
    """
    Khazad command line interface.
    """

    def __init__(self):
        os.environ["HF_HOME"] = str(ConfigManager.USER_DATA_DIR / "models" / "huggingface")
        os.environ["TORCH_HOME"] = str(ConfigManager.USER_DATA_DIR / "models" / "torch")

    @staticmethod
    def _run_calibration(mode: str):
        """Launch the calibration script for the given mode."""
        if mode == "retail":
            from .calibrate_retail import main as calibrate_main
        elif mode == "echoes":
            from .calibrate_echoes import main as calibrate_main
        else:
            from .calibrate_static import main as calibrate_main
        calibrate_main()


    @staticmethod
    def _run_voice_lab():
        """Launch the Voice Lab configuration suite."""
        from .voice_lab.ui import create_ui

        demo = create_ui()
        demo.launch(inbrowser=True)


    @staticmethod
    def _run_install_plugin():
        """Install the getNPCNames LOTRO plugin to the user's Documents folder."""
        import shutil

        base_dir = ConfigManager._find_project_root()
        src_plugin = base_dir / "plugins" / "Dt192"
        if not src_plugin.exists():
            print(f"ERROR: Plugin source not found at {src_plugin}")
            return

        # Standard LOTRO plugin directory
        lotro_plugins = (
            Path.home() / "Documents" / "The Lord of the Rings Online" / "Plugins"
        )
        dst_plugin = lotro_plugins / "Dt192"

        if dst_plugin.exists():
            print(f"Plugin already installed at {dst_plugin}")
            print("Updating...")
            shutil.rmtree(dst_plugin)

        shutil.copytree(src_plugin, dst_plugin)
        print(f"Plugin installed to {dst_plugin}")
        print("You may need to reload plugins in-game with /plugins refresh")


    @staticmethod
    def print_header():
        """Print the startup banner."""
        print(r"""
        ========================================
           LOTRO NARRATOR - AI VOICE OVER
        ========================================
        """)


    @staticmethod
    def get_args():
        """Parse and return CLI arguments."""
        parser = argparse.ArgumentParser(
            description="Khazad Voice TTS – AI Narrator for LOTRO"
        )
        parser.add_argument(
            "--mode", choices=["retail", "static", "echoes"], help="Game mode to start in"
        )
        parser.add_argument(
            "--device", choices=["gpu", "cpu"], help="Audio engine to start in"
        )
        parser.add_argument(
            "--calibrate",
            choices=["retail", "echoes", "static"],
            help="Run calibration for the given game mode",
        )
        parser.add_argument(
            "--voice-lab",
            action="store_true",
            help="Launch the Voice Lab configuration suite",
        )
        parser.add_argument(
            "--voice-mix",
            action="store_true",
            help="[Experimental] Use separate voices for NPC dialogue (quoted) and narrator text",
        )
        parser.add_argument(
            "--install-retail-plugin",
            action="store_true",
            help="Install the getNPCNames LOTRO plugin",
        )
        return parser.parse_args()


    @staticmethod
    def _select_device() -> str:
        """Prompt the user to choose a TTS backend."""
        print("\n[SELECT AUDIO ENGINE]")
        print("1. CPU (Kokoro) [Default]")
        print("   -> Fast, Reliable. Works on all PCs.")
        print("2. GPU (OmniVoice)")
        print("   -> Higher Quality. REQUIRES NVIDIA GPU.")
        device_input = input("\nEnter choice (1 or 2): ").strip()
        return "gpu" if device_input == "2" else "cpu"


    def get_device_arg(self, args: argparse.Namespace) -> str:
        """Return the TTS backend choice from *args* or prompt the user."""
        if args.device:
            return args.device
        return self._select_device()


    def _interactive_menu(self):
        """Show an interactive menu when launched with no arguments."""
        print("What would you like to do?\n")
        print("  1. Start Retail Mode (Auto-detect quest window)")
        print("  2. Start Echoes of Angmar Mode")
        print("  3. Start Static Mode (Fixed quest window)")
        print("  4. Calibrate Retail")
        print("  5. Calibrate Echoes of Angmar")
        print("  6. Calibrate Static Mode")
        print("  7. Voice Lab & Configuration")
        print("  8. Install LOTRO Plugin")
        print("  9. Start Retail Mode + Voice Mix (Experimental)")
        print(" 10. Start Echoes Mode + Voice Mix (Experimental)")
        print(" 11. Start Static Mode + Voice Mix (Experimental)")
        print()

        choice = input("Enter choice (1-11): ").strip()

        match choice:
            case "1":
                EngineStartup("retail", self._select_device())
            case "2":
                EngineStartup("echoes", self._select_device())
            case "3":
                EngineStartup("static", self._select_device())
            case "4":
                self._run_calibration("retail")
            case "5":
                self._run_calibration("echoes")
            case "6":
                self._run_calibration("static")
            case "7":
                self._run_voice_lab()
            case "8":
                self._run_install_plugin()
            case "9":
                EngineStartup("retail", self._select_device(), voice_mix=True)
            case "10":
                EngineStartup("echoes", self._select_device(), voice_mix=True)
            case "11":
                EngineStartup("static", self._select_device(), voice_mix=True)
            case _:
                print(f"Invalid choice: {choice}")


    def start(self):
        """Main entry point for Khazad-Voice TTS."""
        self.print_header()

        args = self.get_args()

        if args.calibrate:
            self._run_calibration(args.calibrate)
            return

        if args.voice_lab:
            self._run_voice_lab()
            return

        if args.install_retail_plugin:
            self._run_install_plugin()
            return

        if args.mode:
            EngineStartup(args.mode, self.get_device_arg(args), voice_mix=args.voice_mix)
        else:
            self._interactive_menu()
