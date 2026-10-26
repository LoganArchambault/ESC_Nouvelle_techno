"""Harnais privé de tests; absent du paquet installé et de toutes les routes."""

from copy import deepcopy
from itertools import count

from blackjack.memory import MemoryStore
from blackjack.model import Limits, PROTOCOL, fresh_deck
from blackjack.sessions import SessionService, unwrap


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def ordered_deck(ranks):
    available = fresh_deck()
    prefix = []
    for rank in ranks.split():
        card = next(c for c in available if c.rank == rank)
        available.remove(card)
        prefix.append(card)
    return prefix + available


class Harness:
    def __init__(self, *, store=None, limits=None):
        self.store = store if store is not None else MemoryStore()
        self.clock = Clock()
        self.limits = limits or Limits(100, 1000, 500, 100)
        identifiers = count()
        self.service = SessionService(self.store, self.limits, clock=self.clock, seed=7,
                                      new_id=lambda: "id-" + str(next(identifiers)))
        self.sequence = count()
        self.observation = None

    def send(self, command, *, request_id=None, revision=None, owner="team-a", **fields):
        payload = {"protocol_version": PROTOCOL,
                   "request_id": request_id or "req-" + str(next(self.sequence)), **fields}
        session_id = None
        if command != "create":
            session_id = self.observation["session_id"]
            payload["expected_revision"] = self.observation["revision"] if revision is None else revision
        result = unwrap(self.service.command(owner, command, payload, session_id))
        self.observation = result
        return result

    def create(self):
        return self.send("create", config_ref="fixture", model_ref="command-script")

    def fixture(self, ranks, *, bankroll=1000, remaining=52):
        self.create()
        with self.store.transaction() as tx:
            session = tx.get_session(self.observation["session_id"])
            session.deck = ordered_deck(ranks)[:remaining]
            session.shoe_id = "fixture-shoe"
            session.bankroll = bankroll
            tx.put_session(session)
        return self.send("start")

    def state(self):
        with self.store.transaction() as tx:
            session = tx.get_session(self.observation["session_id"])
            result = deepcopy(vars(session))
            result["rng"] = session.rng.getstate()
            return result

    def observe(self):
        return unwrap(self.service.observe("team-a", self.observation["session_id"]))
