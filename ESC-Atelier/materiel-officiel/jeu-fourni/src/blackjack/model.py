"""État privé et valeurs de configuration; jamais sérialisés vers un client."""

from dataclasses import dataclass, field
from math import isfinite
from random import Random

PROTOCOL = "esc-api-v1"
RULESET = "esc-blackjack-a26-v1"
STAKE = 50
INITIAL_BANKROLL = 1000
GOAL = 2000
SHOE_THRESHOLD = 18
RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
SUITS = ("clubs", "diamonds", "hearts", "spades")


@dataclass(frozen=True)
class Limits:
    max_hands: int
    max_seconds: float
    idle_seconds: float
    retention_seconds: float

    def __post_init__(self):
        if type(self.max_hands) is not int or self.max_hands <= 0:
            raise ValueError("max_hands doit être un entier positif.")
        for value in (self.max_seconds, self.idle_seconds, self.retention_seconds):
            if type(value) not in (int, float) or not isfinite(value) or value <= 0:
                raise ValueError("Les durées doivent être positives et finies.")


@dataclass(frozen=True)
class Card:
    rank: str
    suit: str

    def public(self):
        return {"rank": self.rank, "suit": self.suit}


def fresh_deck():
    return [Card(rank, suit) for rank in RANKS for suit in SUITS]


def hand_value(cards):
    minimum = sum(1 if c.rank == "A" else 10 if c.rank in ("J", "Q", "K")
                  else int(c.rank) for c in cards)
    usable = any(c.rank == "A" for c in cards) and minimum + 10 <= 21
    return minimum + (10 if usable else 0), usable


@dataclass
class Session:
    session_id: str
    owner: str
    limits: Limits
    created_at: float
    last_activity: float
    rng: Random
    config_ref: str = ""
    model_ref: str = ""
    revision: int = 0
    bankroll: int = INITIAL_BANKROLL
    bankroll_before_hand: int | None = None
    bet_pending: int = 0
    session_status: str = "active"
    end_reason: str | None = None
    finished_at: float | None = None
    hand_status: str = "ready"
    hand_id: str | None = None
    hands_settled: int = 0
    shoe_id: str | None = None
    shoe_reset: bool = False
    deck: list[Card] = field(default_factory=list)
    player: list[Card] = field(default_factory=list)
    dealer: list[Card] = field(default_factory=list)
    visible_events: list[dict] = field(default_factory=list)
    event_count: int = 0
    result: dict | None = None
