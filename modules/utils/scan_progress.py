import json
import os
import datetime

STATE_FILE = os.path.join(os.path.dirname(__file__), "scan_state.json")

class ScanProgressManager:
    """
    Manages persistent state for long-running scans.
    Saves progress to a local JSON file to allow resuming after crashes/refreshes.
    """
    
    def __init__(self):
        self.state_file = STATE_FILE
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.state_file):
            self.util_save_state({
                "active_scan": False,
                "scan_type": None,
                "start_time": None,
                "total_targets": [],
                "completed_targets": [],
                "current_target": None
            })

    def load_state(self):
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            # Reset to clean default state instead of recursing
            default_state = {
                "active_scan": False,
                "scan_type": None,
                "start_time": None,
                "total_targets": [],
                "completed_targets": [],
                "current_target": None
            }
            self.util_save_state(default_state)
            return default_state

    def util_save_state(self, state):
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=4)

    def start_new_scan(self, scan_type, target_list, target_date_str=None):
        """Initializes a fresh scan state."""
        state = {
            "active_scan": True,
            "scan_type": scan_type,
            "target_date": target_date_str,
            "start_time": str(datetime.datetime.now()),
            "total_targets": target_list,
            "completed_targets": [],
            "current_target": None
        }
        self.util_save_state(state)

    def mark_target_start(self, target):
        """Updates state to show we are currently working on a target."""
        state = self.load_state()
        if not state.get("active_scan"): return
        
        state["current_target"] = target
        self.util_save_state(state)

    def mark_target_complete(self, target):
        """Moves a target from pending to completed."""
        state = self.load_state()
        if not state.get("active_scan"): return
        
        if target not in state["completed_targets"]:
            state["completed_targets"].append(target)
        
        state["current_target"] = None # Idle
        self.util_save_state(state)

    def finish_scan(self):
        """Marks the scan as fully complete/inactive."""
        state = self.load_state()
        state["active_scan"] = False
        state["current_target"] = None
        self.util_save_state(state)

    def get_resume_info(self):
        """
        Returns info needed to resume:
        - active: bool
        - remaining_targets: list
        - progress_str: "5/20"
        """
        state = self.load_state()
        if not state.get("active_scan"):
            return None

        total = state.get("total_targets", [])
        done = state.get("completed_targets", [])
        
        # Calculate remaining ensuring order is preserved from total
        remaining = [t for t in total if t not in done]
        
        if not remaining:
            # If active but no remaining, it's effectively done
            self.finish_scan()
            return None
            
        return {
            "type": state.get("scan_type"),
            "target_date": state.get("target_date"),
            "remaining": remaining,
            "completed_count": len(done),
            "total_count": len(total),
            "last_target": state.get("current_target") # Might be stuck here
        }

    def clear_state(self):
        """Force resets the state (User verification: 'Cancel Scan')."""
        self.finish_scan()
