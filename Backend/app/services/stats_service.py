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
        
        # In-memory stats for today
        self.stats_today = {
            "total": 0,
            "authorized": 0,
            "unauthorized": 0,
            "suspicious": 0,
            "hourly_trend": defaultdict(int)
        }
        self.week_total = 0
        self.last_init_date = datetime.now().date()
        
        # Initialize stats from file once
        self._initialize_from_file()

    def _ensure_file(self):
        if not os.path.exists(STATS_FILE):
            with open(STATS_FILE, 'w', encoding='utf-8') as f:
                pass

    def _initialize_from_file(self):
        """Read file once on startup to populate counters"""
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        seven_days_ago = now - timedelta(days=7)
        
        try:
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        event = json.loads(line)
                        ts = event.get("timestamp", 0)
                        dt = datetime.fromtimestamp(ts)
                        
                        if dt > seven_days_ago:
                            self.week_total += 1
                            if dt.date() == now.date():
                                self._increment_counters(event, dt)
                    except:
                        continue
        except Exception as e:
            print(f"Error initializing stats from file: {e}")

    def _increment_counters(self, event: Dict, dt: datetime):
        self.stats_today["total"] += 1
        etype = event.get("type", "").upper()
        if "AUTHORIZED" in etype and "UNAUTHORIZED" not in etype:
            self.stats_today["authorized"] += 1
        elif "UNAUTHORIZED" in etype:
            self.stats_today["unauthorized"] += 1
        elif "SUSPICIOUS" in etype or "BEHAVIOR" in etype or "RUNNING" in etype or "RESTRICTED" in etype:
            self.stats_today["suspicious"] += 1
        
        hour_key = dt.strftime("%H:00")
        self.stats_today["hourly_trend"][hour_key] += 1

    def log_event(self, event_type: str, data: Dict):
        """Log an event and update in-memory counters."""
        now = datetime.now()
        
        # Reset daily counters if date changed
        if now.date() != self.last_init_date:
            self.stats_today = {
                "total": 0, "authorized": 0, "unauthorized": 0, 
                "suspicious": 0, "hourly_trend": defaultdict(int)
            }
            self.last_init_date = now.date()

        entry = {
            "timestamp": time.time(),
            "datetime": now.isoformat(),
            "type": event_type,
            **data
        }
        
        self.week_total += 1
        self._increment_counters(entry, now)
        
        with self._lock:
            with open(STATS_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + "\n")
        
        return entry

    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """Read last N lines efficiently using file seeking."""
        events = []
        try:
            if not os.path.exists(STATS_FILE):
                return []
            
            with open(STATS_FILE, 'rb') as f:
                f.seek(0, os.SEEK_END)
                file_size = f.tell()
                
                buffer_size = 8192
                buffer = b""
                pos = file_size
                
                while len(events) < limit and pos > 0:
                    read_len = min(pos, buffer_size)
                    pos -= read_len
                    f.seek(pos)
                    chunk = f.read(read_len)
                    buffer = chunk + buffer
                    
                    lines = buffer.split(b"\n")
                    buffer = lines[0]
                    for line in reversed(lines[1:]):
                        if not line.strip(): continue
                        try:
                            events.append(json.loads(line.decode('utf-8')))
                            if len(events) >= limit: break
                        except:
                            continue
                
                if len(events) < limit and buffer.strip():
                    try:
                        events.append(json.loads(buffer.decode('utf-8')))
                    except:
                        pass
        except Exception as e:
            print(f"Error reading stats: {e}")
            
        return events

    def get_stats_summary(self) -> Dict:
        """Return stats instantly from memory."""
        return {
            "today_total": self.stats_today["total"],
            "today_authorized": self.stats_today["authorized"],
            "today_unauthorized": self.stats_today["unauthorized"],
            "today_suspicious": self.stats_today["suspicious"],
            "week_total": self.week_total,
            "hourly_trend": dict(self.stats_today["hourly_trend"])
        }

# Global Instance
stats_service = StatsService()
