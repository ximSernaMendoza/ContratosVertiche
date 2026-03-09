from __future__ import annotations

from datetime import date
from dateutil.relativedelta import relativedelta


class CalendarService:
    @staticmethod
    def alert_date(expiry: date) -> date:
        return expiry - relativedelta(months=3)

    def compute_alerts(self, contracts: list[dict], today: date) -> list[dict]:
        alerts = []
        for c in contracts:
            exp = c["expiry"]
            start_alert = self.alert_date(exp)
            if start_alert <= today <= exp:
                alerts.append({
                    **c,
                    "alert_start": start_alert,
                    "days_left": (exp - today).days
                })
        alerts.sort(key=lambda x: x["days_left"])
        return alerts

    def build_calendar_events(self, contracts: list[dict]) -> list[dict]:
        events = []
        for c in contracts:
            exp = c["expiry"]
            start_alert = self.alert_date(exp)

            # extendedProps SOLO con strings/números
            safe_props = {
                "type": "alert",
                "id": str(c.get("id", "")),
                "title": str(c.get("title", "")),
                "state": str(c.get("state", "")),
                "expiry": exp.isoformat(),                 #
                "alert_start": start_alert.isoformat(),    
            }

            events.append({
                "title": f"⚠️ Alerta (3m) · {c['id']}",
                "start": start_alert.isoformat(),  
                "allDay": True,
                "extendedProps": safe_props
            })

            safe_props2 = dict(safe_props)
            safe_props2["type"] = "expiry"

            events.append({
                "title": f"⛔ Vence · {c['id']}",
                "start": exp.isoformat(),         
                "allDay": True,
                "extendedProps": safe_props2
            })

        return events
