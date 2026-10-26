"""Liste blanche publique : aucune sérialisation générique de l'état privé."""

from .model import PROTOCOL, RULESET, hand_value


def observe(session):
    resolved = session.hand_status == "hand_over"
    dealer = session.dealer if resolved else session.dealer[:1]
    player_total, usable = hand_value(session.player) if session.player else (None, None)
    deadline = min(session.created_at + session.limits.max_seconds,
                   session.last_activity + session.limits.idle_seconds)
    return {
        "protocol_version": PROTOCOL, "ruleset_id": RULESET,
        "session_id": session.session_id, "hand_id": session.hand_id,
        "revision": session.revision, "session_status": session.session_status,
        "end_reason": session.end_reason, "hand_status": session.hand_status,
        "bankroll": session.bankroll, "bankroll_before_hand": session.bankroll_before_hand,
        "bet_pending": session.bet_pending, "player_cards": [c.public() for c in session.player],
        "player_total": player_total, "player_usable_ace": usable,
        "dealer_upcard": session.dealer[0].public() if session.dealer else None,
        "dealer_cards": [c.public() for c in dealer],
        "dealer_total": hand_value(session.dealer)[0] if resolved else None,
        "legal_actions": ["hit", "hold"] if session.hand_status == "decision"
        and session.session_status == "active" else [],
        "shoe_id": session.shoe_id, "shoe_reset": session.shoe_reset,
        "visible_events": session.visible_events, "result": session.result,
        "limits": {"max_hands": session.limits.max_hands,
                   "max_seconds": session.limits.max_seconds,
                   "idle_seconds": session.limits.idle_seconds,
                   "retention_seconds": session.limits.retention_seconds,
                   "expires_at": deadline, "hands_settled": session.hands_settled},
    }
