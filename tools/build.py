import subprocess
import sys

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        if self.target_name == "wheel":
            self.app.display_info("📜 Compiling manpages…")
            subprocess.run(
                [sys.executable, "-m", "tools.compile_manpages"],
                check=True,
            )
