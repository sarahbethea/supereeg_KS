import subprocess
import time
import json
import logging
import traceback
from datetime import datetime
from typing import List, Dict, Optional

class SlurmJobManager:
    def __init__(self, max_jobs=10, user=None, error_log_file="slurm_errors.log"):
        self.max_jobs = max_jobs
        self.user = user
        self.submitted_jobs = []
        self.error_log_file = error_log_file
        
        # Setup error logging
        self.setup_error_logging()
    
    def setup_error_logging(self):
        """Initialize error logging system"""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.ERROR)
        
        # File handler for errors
        file_handler = logging.FileHandler(self.error_log_file)
        file_handler.setLevel(logging.ERROR)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        # Add handler if not already added
        if not self.logger.handlers:
            self.logger.addHandler(file_handler)
    
    def save_error(self, error_type: str, error_message: str, 
                   details: Optional[Dict] = None):
        """
        Save error to log file and JSON error file
        
        Args:
            error_type: Type of error (e.g., 'subprocess', 'parsing', 'connection')
            error_message: Human-readable error message
            details: Additional error details (job_id, command, etc.)
        """
        # Create error entry
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "message": error_message,
            "details": details or {}
        }
        
        # 1. Log to file using Python's logging
        self.logger.error(f"{error_type}: {error_message}")
        
        # 2. Save to JSON error file (appends to existing errors)
        try:
            # Try to load existing errors
            try:
                with open("errors.json", "r") as f:
                    all_errors = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                all_errors = []
            
            # Add new error
            all_errors.append(error_entry)
            
            # Save back to file
            with open("errors.json", "w") as f:
                json.dump(all_errors, f, indent=2)
                
        except Exception as e:
            # If we can't save to JSON, at least log it
            self.logger.error(f"Failed to save error to JSON: {str(e)}")
    
    # MODIFIED VERSION OF YOUR get_running_jobs WITH ERROR SAVING
    def get_running_jobs(self) -> List[Dict]:
        """Get currently running/pending jobs for the user - WITH ERROR SAVING"""
        if self.user:
            cmd = ["squeue", "-u", self.user, "-o", "%i %T", "--noheader"]
            cmd_details = f"squeue -u {self.user}"
        else:
            cmd = ["squeue", "-o", "%i %T", "--noheader"]
            cmd_details = "squeue"
        
        try:
            # Attempt to run the command
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True,
                timeout=30  # Add timeout
            )
            
            jobs = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        job_id, status = line.split()
                        jobs.append({"job_id": job_id, "status": status})
                    except ValueError as e:
                        # ERROR: Failed to parse line
                        self.save_error(
                            error_type="parsing_error",
                            error_message=f"Failed to parse squeue output line: '{line}'",
                            details={
                                "command": cmd_details,
                                "raw_line": line,
                                "traceback": traceback.format_exc()
                            }
                        )
            return jobs
            
        except subprocess.CalledProcessError as e:
            # ERROR: Command failed (non-zero exit code)
            self.save_error(
                error_type="subprocess_error",
                error_message=f"Command failed with exit code {e.returncode}",
                details={
                    "command": cmd_details,
                    "exit_code": e.returncode,
                    "stderr": e.stderr.strip(),
                    "stdout": e.stdout.strip()
                }
            )
            return []  # Return empty list as fallback
            
        except subprocess.TimeoutExpired as e:
            # ERROR: Command timed out
            self.save_error(
                error_type="timeout_error",
                error_message=f"Command timed out after {e.timeout} seconds",
                details={
                    "command": cmd_details,
                    "timeout": e.timeout
                }
            )
            return []
            
        except FileNotFoundError as e:
            # ERROR: Command not found (squeue not installed/available)
            self.save_error(
                error_type="command_not_found",
                error_message="squeue command not found. Is SLURM installed?",
                details={
                    "command": "squeue",
                    "error": str(e)
                }
            )
            return []
            
        except Exception as e:
            # ERROR: Any other unexpected error
            self.save_error(
                error_type="unexpected_error",
                error_message=f"Unexpected error getting running jobs: {str(e)}",
                details={
                    "command": cmd_details,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
            )
            return []
    
    # MODIFIED count_active_jobs with error handling
    def count_active_jobs(self) -> int:
        """Count running and pending jobs - WITH ERROR SAVING"""
        try:
            jobs = self.get_running_jobs()  # This now saves its own errors
            return len(jobs)
        except Exception as e:
            # ERROR: If get_running_jobs raises an unexpected exception
            self.save_error(
                error_type="count_jobs_error",
                error_message=f"Failed to count active jobs: {str(e)}",
                details={
                    "user": self.user,
                    "traceback": traceback.format_exc()
                }
            )