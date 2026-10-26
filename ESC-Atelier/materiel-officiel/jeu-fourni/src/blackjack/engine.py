"""Règles uniques : aucun réseau, fichier, horloge système ou agent."""

from .errors import GameError
from .model import GOAL, SHOE_THRESHOLD, STAKE, fresh_deck, hand_value


def apply_command(session, command, action, new_id):
    if session.session_status != "active":
        if command == "close":
            return False
        raise GameError("invalid_transition")
    if command == "start":
        _start_hand(session, new_id)
    elif command == "act":
        _act(session, action)
    elif command == "close":
        _begin_transition(session)
        session.session_status = "interrupted"
        session.end_reason = "explicit_close"
    return True


def _begin_transition(session):
    session.shoe_reset = False
    session.visible_events = []


def _start_hand(session, new_id):
    if session.hand_status == "decision":
        raise GameError("invalid_transition")
    _begin_transition(session)
    if _finish_by_bankroll(session):
        return
    if len(session.deck) < SHOE_THRESHOLD:
        session.deck = fresh_deck()
        session.rng.shuffle(session.deck)
        session.shoe_id = new_id()
        session.shoe_reset = True
    session.hand_id = new_id()
    session.hand_status = "decision"
    session.player, session.dealer = [], []
    session.result = None
    session.bankroll_before_hand = session.bankroll
    session.bankroll -= STAKE
    session.bet_pending = STAKE
    _draw_visible(session, "player")
    _draw_visible(session, "dealer")
    _draw_visible(session, "player")
    session.dealer.append(session.deck.pop(0))
    player_natural = hand_value(session.player)[0] == 21
    dealer_natural = hand_value(session.dealer)[0] == 21
    if player_natural or dealer_natural:
        _reveal_hole(session)
        outcome, reason = ("tie", "both_natural") if player_natural and dealer_natural else (
            ("win", "player_natural") if player_natural else ("loss", "dealer_natural"))
        _settle(session, outcome, reason)


def _act(session, action):
    if session.hand_status != "decision":
        raise GameError("invalid_transition")
    _begin_transition(session)
    if action == "hold":
        _play_dealer(session)
        return
    _draw_visible(session, "player")
    total = hand_value(session.player)[0]
    if total > 21:
        _reveal_hole(session)
        _settle(session, "loss", "player_bust")
    elif total == 21:
        _play_dealer(session)


def _play_dealer(session):
    _reveal_hole(session)
    while hand_value(session.dealer)[0] < 17:
        _draw_visible(session, "dealer")
    dealer_total, _ = hand_value(session.dealer)
    player_total, _ = hand_value(session.player)
    if dealer_total > 21:
        _settle(session, "win", "dealer_bust")
    elif player_total == dealer_total:
        _settle(session, "tie", "equal_total")
    elif player_total > dealer_total:
        _settle(session, "win", "higher_total")
    else:
        _settle(session, "loss", "lower_total")


def _draw_visible(session, owner):
    card = session.deck.pop(0)
    getattr(session, owner).append(card)
    _emit(session, owner, card)


def _reveal_hole(session):
    _emit(session, "dealer", session.dealer[1])


def _emit(session, owner, card):
    session.event_count += 1
    session.visible_events.append({"event_id": str(session.event_count),
                                   "shoe_id": session.shoe_id, "hand_id": session.hand_id,
                                   "owner": owner, "card": card.public()})


def _settle(session, outcome, reason):
    credit = {"win": 100, "tie": 50, "loss": 0}[outcome]
    session.bankroll += credit
    session.bet_pending = 0
    session.hand_status = "hand_over"
    session.hands_settled += 1
    session.result = {"outcome": outcome, "reason": reason, "stake": STAKE,
                      "credit": credit, "net_gain": credit - STAKE,
                      "bankroll_before": session.bankroll_before_hand,
                      "bankroll_after": session.bankroll}
    if not _finish_by_bankroll(session) and session.hands_settled >= session.limits.max_hands:
        session.session_status = "truncated"
        session.end_reason = "hand_limit"


def _finish_by_bankroll(session):
    if session.bankroll >= GOAL:
        session.session_status, session.end_reason = "goal_reached", "goal_reached"
        return True
    if session.bankroll < STAKE:
        session.session_status, session.end_reason = "ruin", "ruin"
        return True
    return False
