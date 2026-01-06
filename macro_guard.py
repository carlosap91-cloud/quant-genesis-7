from datetime import datetime, time

class MacroGuard:
    def __init__(self):
        # Simulated economic calendar for critical events
        # Format: "YYYY-MM-DD": ["Event Name", "HH:MM"] (Time in CET)
        self.calendar = {
            "2026-01-07": ["BCE Interest Rate Decision", "14:15"],
            "2026-01-15": ["FED Interest Rate Decision", "20:00"],
            "2026-01-20": ["Eurozone CPI", "11:00"]
        }
        
    def check_market_status(self):
        """
        Checks if current time is within a danger window (2h before/after critical event).
        Returns: (is_safe: bool, message: str)
        """
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        
        if today_str in self.calendar:
            event_name, event_time_str = self.calendar[today_str]
            event_hour, event_minute = map(int, event_time_str.split(":"))
            
            event_dt = now.replace(hour=event_hour, minute=event_minute, second=0, microsecond=0)
            diff_hours = (now - event_dt).total_seconds() / 3600
            
            # Danger Zone: -2h to +2h
            if -2 <= diff_hours <= 2:
                return False, f"⛔ ALERTA MACRO: {event_name} a las {event_time_str}. Mercado Bloqueado por Seguridad."
            elif diff_hours < -2:
                return True, f"⚠️ PRECAUCIÓN: {event_name} hoy a las {event_time_str}."
            
        return True, "✅ Mercado Normal. Sin eventos macroeconómicos inminentes."

if __name__ == "__main__":
    guard = MacroGuard()
    is_safe, msg = guard.check_market_status()
    print(msg)
