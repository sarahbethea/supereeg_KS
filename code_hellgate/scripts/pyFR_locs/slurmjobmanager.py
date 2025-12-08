import subprocess
import time
import json
from typing import List, Dict

class SlurmJobManager:
    def __init__(self, max_jobs=10, user=None):
        self.max_jobs = max_jobs
        self.user = user
        self.submitted_jobs = []
    
    def get_running_jobs(self) -> List[Dict]:
        """Get currently running/pending jobs for the user"""
        if self.user:
            cmd = ["squeue", "-u", self.user, "-o", "%i %T", "--noheader"]
        else:
            cmd = ["squeue", "-o", "%i %T", "--noheader"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            jobs = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    job_id, status = line.split()
                    jobs.append({"job_id": job_id, "status": status})
            return jobs
        except subprocess.CalledProcessError:
            return []
    
    def count_active_jobs(self) -> int:
        """Count running and pending jobs"""
        jobs = self.get_running_jobs()
        return len(jobs)
