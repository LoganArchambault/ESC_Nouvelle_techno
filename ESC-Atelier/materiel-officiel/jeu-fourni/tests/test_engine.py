"""Oracles indépendants T01–T23/T25 du contrat adopté."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from collections import Counter
from itertools import product
import json
import unittest

from blackjack import GameError, Limits, LocalClient
from blackjack.model import PROTOCOL, fresh_deck, hand_value
from blackjack.validation import parse_json
from support import Harness, ordered_deck

PUBLIC_KEYS = set("protocol_version ruleset_id session_id hand_id revision session_status "
                  "end_reason hand_status bankroll bankroll_before_hand bet_pending player_cards "
                  "player_total player_usable_ace dealer_upcard dealer_cards dealer_total legal_actions "
                  "shoe_id shoe_reset visible_events result limits".split())


class EngineTests(unittest.TestCase):
    def assert_result(self, observation, outcome, reason, bankroll):
        result = observation["result"]
        self.assertEqual((result["outcome"], result["reason"], observation["bankroll"]),
                         (outcome, reason, bankroll))
        self.assertEqual(result["bankroll_before"] + result["net_gain"], bankroll)
        self.assertEqual(result["net_gain"], result["credit"] - 50)
        self.assertEqual(observation["bet_pending"], 0)
        self.assertEqual(observation["legal_actions"], [])
        self.assertEqual(observation["hand_status"], "hand_over")
        if not any(c["rank"] == "A" for c in observation["dealer_cards"]):
            self.assertEqual(observation["dealer_total"], sum(
                10 if c["rank"] in ("J", "Q", "K") else int(c["rank"])
                for c in observation["dealer_cards"]))

    def test_T01_deck(self):
        deck = fresh_deck()
        self.assertEqual(len(set(deck)), 52)
        self.assertEqual(set(Counter(c.rank for c in deck).values()), {4})
        h = Harness()
        initial = h.create()
        self.assertEqual(initial["bankroll"], 1000)
        self.assertIsNone(initial["shoe_id"])
        self.assertEqual(initial["hand_status"], "ready")
        self.assertEqual(initial["player_cards"], [])

    def test_T02_reset_17_keep_18_and_first(self):
        for remaining, reset in [(17, True), (18, False)]:
            with self.subTest(remaining=remaining):
                h = Harness()
                o = h.fixture("2 6 3 K", remaining=remaining)
                self.assertEqual(o["shoe_reset"], reset)
                self.assertEqual(o["shoe_id"] == "fixture-shoe", not reset)
        h = Harness()
        h.create()
        self.assertTrue(h.send("start")["shoe_reset"])

    def test_T03_distribution_and_hidden_card(self):
        h = Harness()
        o = h.fixture("2 6 3 K")
        self.assertEqual([c["rank"] for c in o["player_cards"]], ["2", "3"])
        self.assertEqual(o["player_total"], 5)
        self.assertEqual([c["rank"] for c in o["dealer_cards"]], ["6"])
        self.assertIsNone(o["dealer_total"])
        self.assertEqual(o["bankroll"], 950)
        self.assertEqual(o["bet_pending"], 50)
        self.assertEqual(o["legal_actions"], ["hit", "hold"])
        self.assertNotIn('"K"', json.dumps(o))
        self.assertEqual([e["card"]["rank"] for e in o["visible_events"]], ["2", "6", "3"])
        self.assertEqual([e["event_id"] for e in o["visible_events"]], ["1", "2", "3"])
        self.assertEqual(o["revision"], 1)

    def test_T04_multiple_aces(self):
        for ranks, total, usable in [("A A", 12, True), ("A 6", 17, True),
                                    ("A 6 10", 17, False), ("A A 9", 21, True),
                                    ("A A 9 10", 21, False), ("K Q 2", 22, False)]:
            with self.subTest(ranks=ranks):
                self.assertEqual(hand_value(ordered_deck(ranks)[:len(ranks.split())]), (total, usable))

    def test_T05_player_natural(self):
        self.assert_result(Harness().fixture("A 9 K 7"), "win", "player_natural", 1050)

    def test_T06_both_natural(self):
        self.assert_result(Harness().fixture("A A K Q"), "tie", "both_natural", 1000)

    def test_T07_dealer_natural(self):
        self.assert_result(Harness().fixture("10 A 9 K"), "loss", "dealer_natural", 950)

    def test_T08_natural_no_dealer_draw(self):
        h = Harness()
        self.assert_result(h.fixture("A 10 K 6 5"), "win", "player_natural", 1050)
        self.assertEqual(h.state()["deck"][0].rank, "5")
        self.assertEqual([e["owner"] for e in h.observation["visible_events"]],
                         ["player", "dealer", "player", "dealer"])

    def test_T09_player_bust_reveals_without_dealer_draw(self):
        h = Harness()
        h.fixture("10 8 9 7 5 2")
        o = h.send("act", action="hit")
        self.assert_result(o, "loss", "player_bust", 950)
        self.assertEqual(o["player_total"], 24)
        self.assertEqual([c["rank"] for c in o["dealer_cards"]], ["8", "7"])
        self.assertEqual(h.state()["deck"][0].rank, "2")
        before = h.state()
        with self.assertRaises(GameError) as raised:
            h.send("act", action="hold")
        self.assertEqual(raised.exception.code, "invalid_transition")
        self.assertEqual(before, h.state())

    def test_T10_hit_21_automatic(self):
        h = Harness()
        h.fixture("10 10 5 7 6")
        self.assert_result(h.send("act", action="hit"), "win", "higher_total", 1050)
        self.assertEqual(h.observation["player_total"], 21)

    def test_T11_dealer_independent_and_soft17(self):
        h = Harness()
        h.fixture("10 8 3 6 3")
        self.assert_result(h.send("act", action="hold"), "loss", "lower_total", 950)
        self.assertEqual(h.observation["dealer_total"], 17)
        h = Harness()
        h.fixture("10 A 9 6 3")
        self.assert_result(h.send("act", action="hold"), "win", "higher_total", 1050)
        self.assertEqual(len(h.observation["dealer_cards"]), 2)
        self.assertEqual(h.state()["deck"][0].rank, "3")

    def test_T12_dealer_bust_or_twenty(self):
        for rank, outcome, reason, bankroll in [("K", "win", "dealer_bust", 1050),
                                               ("4", "loss", "lower_total", 950)]:
            h = Harness()
            h.fixture("10 10 9 6 " + rank)
            self.assert_result(h.send("act", action="hold"), outcome, reason, bankroll)

    def test_T13_tie_win_loss(self):
        for rank, outcome, reason, bankroll in [("8", "tie", "equal_total", 1000),
                                               ("7", "win", "higher_total", 1050),
                                               ("9", "loss", "lower_total", 950)]:
            h = Harness()
            h.fixture("10 K 8 " + rank)
            self.assert_result(h.send("act", action="hold"), outcome, reason, bankroll)

    def test_T14_ruin(self):
        h = Harness()
        h.fixture("10 K 8 9", bankroll=50)
        self.assertEqual(h.observation["session_status"], "active")
        o = h.send("act", action="hold")
        self.assert_result(o, "loss", "lower_total", 0)
        self.assertEqual(o["session_status"], "ruin")
        h = Harness()
        o = h.fixture("2 6 3 K", bankroll=25)
        self.assertEqual((o["bankroll"], o["session_status"], o["hand_id"]), (25, "ruin", None))
        self.assertEqual(len(h.state()["deck"]), 52)
        self.assertEqual(o["bet_pending"], 0)

    def test_T15_goal_and_new_session(self):
        h = Harness()
        o = h.fixture("A 9 K 7", bankroll=1950)
        self.assertEqual((o["bankroll"], o["session_status"]), (2000, "goal_reached"))
        h = Harness()
        o = h.fixture("2 6 3 K", bankroll=2000)
        self.assertIsNone(o["hand_id"])
        self.assertEqual(o["bankroll"], 2000)
        old = deepcopy(o)
        h.create()
        o = h.send("start")
        self.assertNotEqual(old["session_id"], o["session_id"])
        self.assertNotEqual(old["shoe_id"], o["shoe_id"])
        self.assertEqual(o["bankroll_before_hand"], 1000)

    def test_T16_explicit_next_hand(self):
        h = Harness()
        terminal = h.fixture("A 9 K 7")
        self.assertEqual(terminal["result"], h.observe()["result"])
        self.assertEqual(terminal["hand_id"], h.observe()["hand_id"])
        o = h.send("start")
        self.assertNotEqual(terminal["hand_id"], o["hand_id"])
        self.assertEqual(o["limits"]["hands_settled"], 1 if o["result"] is None else 2)

    def test_T17_replay_events_and_no_duplicate_cards(self):
        h = Harness()
        h.fixture("10 8 9 7 5")
        o = h.send("act", action="hit", request_id="once")
        state = h.state()
        replay = h.send("act", action="hit", request_id="once", revision=1)
        self.assertEqual(o, replay)
        self.assertEqual(state, h.state())
        reread = h.observe()
        self.assertEqual(o["visible_events"], reread["visible_events"])
        self.assertFalse(reread["shoe_reset"])
        cards = {e["event_id"]: e["card"] for e in o["visible_events"] + reread["visible_events"]}
        self.assertEqual(len(cards), 2)

    def test_T18_long_hand_18_cards_and_aces(self):
        # Toutes les cartes faibles sont distinctes. Deux ordres de cartes adverses.
        for ranks in ["A 4 A 4 A A 2 2 2 2 3 3 3 3 4 4 5 5",
                      "2 A 2 A A A 2 2 3 3 3 3 4 4 4 4 5 5"]:
            h = Harness()
            o = h.fixture(ranks, remaining=18)
            decisions = 0
            while o["legal_actions"]:
                o = h.send("act", action="hit")
                self.assertEqual(o["shoe_id"], "fixture-shoe")
                self.assertFalse(o["shoe_reset"])
                decisions += 1
            self.assertGreaterEqual(decisions, 6)
            self.assertLessEqual(len(h.state()["player"]) + len(h.state()["dealer"]), 18)
            self.assertIsNotNone(o["result"])
        cheapest = sorted(1 if c.rank == "A" else 10 if c.rank in ("J", "Q", "K")
                          else int(c.rank) for c in fresh_deck())
        self.assertEqual(sum(cheapest[:18]), 50)
        self.assertEqual(sum(cheapest[:19]), 55)

    def test_T19_invalid_requests_atomic(self):
        h = Harness()
        h.fixture("2 6 3 K")
        for command, extra in [("start", {}), ("act", {"action": "hit", "stake": 50}),
                               ("act", {"action": "hit", "seed": 3}),
                               ("act", {"action": "hit", "expected_revision": True})]:
            before = h.state()
            payload = {"protocol_version": PROTOCOL, "expected_revision": 1,
                       "request_id": "bad", **extra}
            with self.assertRaises(GameError):
                h.service.command("team-a", command, payload, h.observation["session_id"])
            self.assertEqual(before, h.state())
        for raw in [b"{", b'{"x":NaN}', b'{"x":1e999}', b'{"x":1,"x":2}', b'"\xff"']:
            with self.assertRaises(GameError) as raised:
                parse_json(raw)
            self.assertEqual(raised.exception.code, "invalid_request")

    def test_T20_action_errors_and_ownership(self):
        h = Harness()
        h.fixture("2 6 3 K")
        with self.assertRaises(GameError) as raised:
            h.send("act", action="split")
        self.assertEqual(raised.exception.status, 422)
        with self.assertRaises(GameError) as raised:
            h.service.observe("team-b", h.observation["session_id"])
        self.assertEqual((raised.exception.status, raised.exception.revision), (404, None))
        h.send("close")
        before = h.state()
        with self.assertRaises(GameError) as raised:
            h.send("act", action="hold")
        self.assertEqual(raised.exception.status, 409)
        self.assertEqual(before, h.state())

    def test_T21_hand_limit_and_goal_priority(self):
        for bankroll, status, reason in [(1000, "truncated", "hand_limit"),
                                         (1950, "goal_reached", "goal_reached")]:
            h = Harness(limits=Limits(1, 1000, 500, 100))
            o = h.fixture("A 9 K 7", bankroll=bankroll)
            self.assertEqual((o["session_status"], o["end_reason"]), (status, reason))
            self.assertEqual(o["limits"]["hands_settled"], 1)

    def test_T22_expiration_reconnect_close_and_retention(self):
        for max_seconds, idle_seconds, status in [(10, 50, "truncated"), (50, 10, "expired")]:
            h = Harness(limits=Limits(100, max_seconds, idle_seconds, 100))
            h.fixture("2 6 3 K")
            state = h.state()
            h.clock.now += 10
            o = h.send("act", action="hit")
            self.assertEqual(o["session_status"], status)
            self.assertEqual(h.state()["deck"], state["deck"])
            self.assertIsNone(o["result"])
            self.assertEqual((o["bankroll_before_hand"], o["bankroll"], o["bet_pending"]),
                             (1000, 950, 50))
            self.assertEqual(o["dealer_cards"], [o["dealer_upcard"]])
            h.clock.now += 100
            from blackjack.sessions import unwrap
            with self.assertRaises(GameError) as raised:
                unwrap(h.service.observe("team-a", o["session_id"]))
            self.assertEqual(raised.exception.status, 410)
        h = Harness()
        o = h.fixture("2 6 3 K")
        h.clock.now += 1
        self.assertEqual(o["player_cards"], h.observe()["player_cards"])
        self.assertEqual(o["revision"], h.observe()["revision"])
        closed = h.send("close")
        self.assertEqual(closed["session_status"], "interrupted")
        self.assertEqual(closed["bet_pending"], 50)
        self.assertIsNone(closed["result"])
        self.assertEqual(closed["revision"], h.send("close")["revision"])

    def test_T23_concurrent_revision_and_idempotency(self):
        h = Harness()
        h.fixture("2 6 3 K 4")
        def mutate(request_id):
            try:
                return h.service.command("team-a", "act", {
                    "protocol_version": PROTOCOL, "request_id": request_id,
                    "expected_revision": 1, "action": "hit"}, h.observation["session_id"])
            except GameError as error:
                return error.code
        with ThreadPoolExecutor(2) as executor:
            results = list(executor.map(mutate, ["one", "two"]))
        self.assertEqual(sum(isinstance(r, dict) for r in results), 1)
        self.assertIn("revision_conflict", results)
        successful_id = "one" if isinstance(results[0], dict) else "two"
        self.assertEqual(mutate(successful_id), next(r for r in results if isinstance(r, dict)))
        with self.assertRaises(GameError) as raised:
            h.service.command("team-a", "act", {"protocol_version": PROTOCOL,
                "request_id": successful_id, "expected_revision": 1, "action": "hold"},
                h.observation["session_id"])
        self.assertEqual(raised.exception.code, "idempotency_conflict")

    def test_T25_public_whitelist_and_return_isolation(self):
        h = Harness()
        o = h.fixture("2 6 3 K")
        self.assertEqual(set(o), PUBLIC_KEYS)
        for event in o["visible_events"]:
            self.assertEqual(set(event), {"event_id", "shoe_id", "hand_id", "owner", "card"})
            self.assertEqual(set(event["card"]), {"rank", "suit"})
        o["visible_events"][0]["card"]["rank"] = "K"
        self.assertEqual(h.observe()["visible_events"][0]["card"]["rank"], "2")
        self.assertEqual(set(GameError("invalid_payload").as_dict()), {"error", "revision"})

    def test_all_four_card_totals_independent_oracle(self):
        # Les as sont évalués par toutes leurs possibilités, sans appeler le calcul du moteur.
        values = [(1, 11), (2,), (6,), (9,), (10,)]
        ranks = ["A", "2", "6", "9", "K"]
        for indexes in product(range(5), repeat=4):
            cards = ordered_deck(" ".join(ranks[i] for i in indexes))[:4]
            totals = [sum(t) for t in product(*(values[i] for i in indexes))]
            acceptable = [t for t in totals if t <= 21]
            expected = max(acceptable) if acceptable else min(totals)
            self.assertEqual(hand_value(cards)[0], expected)

    def test_local_stdlib_only_cycle(self):
        client = LocalClient(Limits(1, 60, 30, 60), seed=3)
        o = client.create_session("smoke", "command-script", "create")
        o = client.start_hand(o["session_id"], o["revision"], "start")
        if o["legal_actions"]:
            o = client.act(o["session_id"], "hold", o["revision"], "command")
        self.assertIsNotNone(o["result"])
        self.assertEqual(o["session_status"], "truncated")

    def test_late_first_access_returns_410_without_settlement(self):
        from blackjack.sessions import unwrap
        for operation in ("read", "replay", "mutation"):
            h = Harness(limits=Limits(1, 10, 5, 10))
            o = h.fixture("2 6 3 K")
            h.clock.now += 100
            with self.assertRaises(GameError) as raised:
                if operation == "read":
                    unwrap(h.service.observe("team-a", o["session_id"]))
                elif operation == "replay":
                    h.send("create", request_id="req-0", config_ref="fixture", model_ref="command-script")
                else:
                    h.send("act", action="hit")
            self.assertEqual(raised.exception.status, 410)

    def test_configuration_strict_types(self):
        for values in [(True, 1, 1, 1), (0, 1, 1, 1), (1, float("nan"), 1, 1),
                       (1, 1, -1, 1), (1, 1, 1, float("inf"))]:
            with self.assertRaises(ValueError):
                Limits(*values)

    def test_memory_transaction_rolls_back_and_old_response_survives_later_revision(self):
        from blackjack.memory import MemoryTransaction
        h = Harness()
        h.fixture("2 6 3 K 4")
        first = h.send("act", action="hit", request_id="once")
        h.send("close")
        before = h.state()
        replay = h.send("act", action="hit", request_id="once", revision=1)
        self.assertEqual(first, replay)
        self.assertEqual(before, h.state())
        original = MemoryTransaction.put_request
        def fail_write(*args):
            raise RuntimeError("fixture")
        MemoryTransaction.put_request = fail_write
        try:
            with self.assertRaises(RuntimeError):
                h.send("create", config_ref="fixture", model_ref="script")
        finally:
            MemoryTransaction.put_request = original
        self.assertEqual(len(h.store._sessions), 1)


if __name__ == "__main__":
    unittest.main()
