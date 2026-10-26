"""Erreurs communes au mode local et au transport."""

ERRORS = {
    "invalid_request": (400, "JSON invalide."),
    "unauthenticated": (401, "Authentification requise."),
    "session_not_found": (404, "Séance introuvable."),
    "revision_conflict": (409, "Révision périmée; relire la séance."),
    "invalid_transition": (409, "Commande impossible dans cet état."),
    "idempotency_conflict": (409, "Identifiant de commande déjà utilisé autrement."),
    "session_gone": (410, "Période de reprise expirée."),
    "invalid_payload": (422, "Champs, types ou valeurs invalides."),
    "unsupported_version": (422, "Version du protocole non soutenue."),
    "rate_limited": (429, "Limite de fréquence atteinte."),
    "service_unavailable": (503, "Service temporairement indisponible."),
}


class GameError(Exception):
    def __init__(self, code, *, revision=None, request_id=None):
        self.code = code
        self.status, self.message = ERRORS[code]
        self.revision = revision
        self.request_id = request_id
        super().__init__(self.message)

    def as_dict(self):
        return {"error": {"code": self.code, "message": self.message,
                          "request_id": self.request_id}, "revision": self.revision}
