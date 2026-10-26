"""Petit client manuel commun aux deux modes; aucune stratégie automatique."""

import argparse
import json
import os
from uuid import uuid4

from blackjack import GameError, Limits, LocalClient
from blackjack.client_https import HTTPSClient, TransportUncertain


def play_one_hand(client, commands):
    """Exécute des commandes imposées par l'appelant, sans choisir d'action."""
    observation = client.create_session("manual-check", "command-script", uuid4().hex)
    observation = client.start_hand(observation["session_id"], observation["revision"], uuid4().hex)
    for action in commands:
        if not observation["legal_actions"]:
            break
        observation = client.act(observation["session_id"], action,
                                 observation["revision"], uuid4().hex)
    return observation


def main():
    parser = argparse.ArgumentParser(description="Vérifier le jeu avec des commandes imposées.")
    parser.add_argument("--url", help="Origine HTTPS; sinon appels locaux directs.")
    parser.add_argument("--actions", nargs="*", choices=("hit", "hold"), required=True)
    parser.add_argument("--max-hands", type=int)
    parser.add_argument("--max-seconds", type=float)
    parser.add_argument("--idle-seconds", type=float)
    parser.add_argument("--retention-seconds", type=float)
    args = parser.parse_args()
    if args.url:
        client = HTTPSClient(args.url, os.environ["BLACKJACK_TOKEN"])
    else:
        bounds = [args.max_hands, args.max_seconds, args.idle_seconds, args.retention_seconds]
        if any(bound is None for bound in bounds):
            parser.error("Les quatre bornes locales doivent être explicites.")
        client = LocalClient(Limits(*bounds))
    try:
        print(json.dumps(play_one_hand(client, args.actions), ensure_ascii=False, indent=2))
    except GameError as error:
        print(json.dumps(error.as_dict(), ensure_ascii=False))
        raise SystemExit(1)
    except TransportUncertain as error:
        # Ce client ponctuel s'arrête : aucune autre commande ou séance n'est créée.
        print(str(error))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
