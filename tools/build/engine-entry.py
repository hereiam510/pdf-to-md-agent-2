"""Frozen entry point. Trusted scripts run only in a separate, explicitly enabled child."""
import runpy
import sys

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--task-script":
        script = sys.argv[2]
        sys.argv = [script]
        runpy.run_path(script, run_name="__main__")
    else:
        from pdfmd.server import main
        main()
