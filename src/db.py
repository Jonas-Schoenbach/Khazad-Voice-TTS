# Imports

# > Standard Library
from typing import Tuple, Optional, List, Dict

# > Third-party imports
import pandas as pd

# > Local dependencies
from .utils import setup_logger
from .config import NPC_DATA_PATH

log = setup_logger(__name__)


class NPCDatabase:
    """
    Manages loading NPC data and providing random samples for selection.
    """
    def __init__(self, csv_path: str = str(NPC_DATA_PATH)):
        self.data = None
        self.all_names = []
        try:
            self.data = pd.read_csv(csv_path)
            # Create a lowercase column for easier searching
            self.data["Name_Lower"] = (
                self.data["Name"].astype(str).str.lower().str.strip()
            )
            self.all_names = sorted(self.data["Name"].dropna().unique().tolist())
            log.info(f"✅ Database loaded: {len(self.data)} NPCs found.")
        except Exception as e:
            log.error(f"❌ Failed to load database: {e}")

    def get_names(self) -> List[str]:
        """Returns all unique NPC names."""
        return self.all_names

    def get_random_npcs(self, count: int = 10) -> List[Dict]:
        """
        Returns a random sample of NPCs from the database.
        Useful for presenting a 'Voice Palette' to the user.

        Parameters
        ----------
        count : int
            Number of random rows to return.

        Returns
        -------
        List[Dict]
            List of NPC records.
        """
        if self.data is None or self.data.empty:
            return []

        # Sample 'count' rows; if DB matches are fewer than count, return all
        sample_size = min(count, len(self.data))
        sample = self.data.sample(n=sample_size)

        return sample.to_dict("records")

    def lookup(self, name: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Exact or Starts-with lookup.
        """
        if self.data is None or not name:
            return None, None

        name_clean = name.lower().strip()

        # 1. Exact Match
        match = self.data[self.data["Name_Lower"] == name_clean]

        # 2. Starts-with Match
        if match.empty:
            match = self.data[self.data["Name_Lower"].str.startswith(name_clean)]

        if not match.empty:
            row = match.iloc[0]
            return row["Gender"], row["Race"]

        return None, None
