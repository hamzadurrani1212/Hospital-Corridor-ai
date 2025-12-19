# app/services/stats_service.py
import json
import time
import os
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict

STATS_FILE = "events.jsonl"

class StatsService:
    def __init__(self):
        self._lock = threading.Lock()
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(STATS_FILE):
            with open(STATS_FILE, 'w') as f:
                pass

    def log_event(self, event_type: str, data: Dict):
        """
        Log an event to the persistent JSONL file.
        """
        entry = {
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            "type": event_type,
            **data
        }
        
        with self._lock:
            with open(STATS_FILE, 'a') as f:
                f.write(json.dumps(entry) + "\n")
        
        return entry

    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """
        Read the last N lines from the file efficiently.
        """
        events = []
        try:
            with self._lock:
                # Read all lines (simple approach for moderate file size)
                # For massive files, we'd read from end, but JSONL allows 'tail' logic
                with open(STATS_FILE, 'r') as f:
                    lines = f.readlines()
                    
                # Parse last 'limit' lines in reverse order
                for line in reversed(lines):
                    if not line.strip(): continue
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
                    if len(events) >= limit:
                        break
        except Exception as e:
            print(f"Error reading stats: {e}")
            
        return events

    def get_stats_summary(self) -> Dict:
        """
        Aggregate stats for dashboard/events page.
        """
        now = datetime.now()
        stats = {
            "today_total": 0,
            "today_authorized": 0,
            "today_unauthorized": 0,
            "today_suspicious": 0,
            "week_total": 0,
            "hourly_trend": defaultdict(int) # "HH:00" -> count
        }
        
        try:
            with self._lock:
                with open(STATS_FILE, 'r') as f:
                    for line in f:
                        if not line.strip(): continue
                        try:
                            event = json.loads(line)
                            ts = event.get("timestamp", 0)
                            dt = datetime.fromtimestamp(ts)
                            
                            # Check if within last 7 days
                            if (now - dt).days < 7:
                                stats["week_total"] += 1
                                
                                # Check if today
                                if dt.date() == now.date():
                                    stats["today_total"] += 1
                                    etype = event.get("type", "").upper()
                                    
                                    if "AUTHORIZED" in etype and "UNAUTHORIZED" not in etype:
                                        stats["today_authorized"] += 1
                                    elif "UNAUTHORIZED" in etype:
                                        stats["today_unauthorized"] += 1
                                    elif "SUSPICIOUS" in etype or "BEHAVIOR" in etype:
                                        stats["today_suspicious"] += 1
                                        
                                    # Hourly trend
                                    hour_key = dt.strftime("%H:00")
                                    stats["hourly_trend"][hour_key] += 1
                        except:
                            continue
                            
        except Exception:
            pass

        return stats

# Global Instance
stats_service = StatsService()
