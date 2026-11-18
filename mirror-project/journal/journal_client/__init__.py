"""Client de la couche journal, pour les couches qui y écrivent (démarches, consentement-minimisation).

- JournalClient.append() lève JournalUnavailable si l'événement n'a pas été inscrit : l'appelant
  annule alors son opération (pas d'action sans trace).
- MemoryJournal : même interface, en mémoire, pour les tests de ces couches.
"""

from .client import JournalClient, JournalUnavailable, journal_from_env
from .memory import MemoryJournal

__all__ = ["JournalClient", "JournalUnavailable", "MemoryJournal", "journal_from_env"]
