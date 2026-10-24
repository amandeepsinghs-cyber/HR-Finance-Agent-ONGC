from .confirm import detect_confirm_intent
try:
    from .coverage import handle_coverage_query, is_coverage_query
except Exception:
    pass
from .ui_control import handle_ui_control
from .greeting import handle_greeting
from .policy import handle_policy
