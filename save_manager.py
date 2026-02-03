"""Save/load manager for BusyBrainPaint.

Handles autosave after each successful fill and loading saved progress.
"""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SaveData:
    """Data structure for saved game state."""

    # Puzzle identifier
    puzzle_path: str

    # Progress state
    filled_regions: list[bool]

    # UI state
    selected_palette: int
    selected_region: int

    # Camera state
    camera_x: float
    camera_y: float
    camera_zoom: float


class SaveManager:
    """Manages saving and loading game progress.

    Saves are stored as JSON files in the saves directory.
    Each puzzle has one save slot (overwrites previous save).
    """

    SAVE_VERSION = 1
    SAVE_DIR = "saves"
    SAVE_FILE = "save.json"

    def __init__(self, base_path: Path | None = None) -> None:
        """Initialize save manager.

        Args:
            base_path: Base directory for saves. Defaults to script directory.
        """
        if base_path is None:
            base_path = Path(__file__).parent
        self.save_dir = base_path / self.SAVE_DIR
        self.save_dir.mkdir(exist_ok=True)

    def _get_save_path(self) -> Path:
        """Get the path to the save file.

        Returns:
            Path to save.json file.
        """
        return self.save_dir / self.SAVE_FILE

    def save(self, data: SaveData) -> bool:
        """Save game state to file.

        Args:
            data: Save data to write.

        Returns:
            True if save succeeded, False otherwise.
        """
        save_dict = {
            "version": self.SAVE_VERSION,
            "puzzle_path": data.puzzle_path,
            "filled_regions": data.filled_regions,
            "selected_palette": data.selected_palette,
            "selected_region": data.selected_region,
            "camera": {
                "x": data.camera_x,
                "y": data.camera_y,
                "zoom": data.camera_zoom,
            },
        }

        try:
            save_path = self._get_save_path()
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(save_dict, f, indent=2)
            return True
        except (OSError, IOError) as e:
            print(f"Failed to save: {e}")
            return False

    def load(self) -> SaveData | None:
        """Load game state from file.

        Returns:
            SaveData if load succeeded, None if no save exists or load failed.
        """
        save_path = self._get_save_path()

        if not save_path.exists():
            return None

        try:
            with open(save_path, "r", encoding="utf-8") as f:
                save_dict = json.load(f)

            # Version check
            version = save_dict.get("version", 0)
            if version != self.SAVE_VERSION:
                print(f"Save version mismatch: {version} != {self.SAVE_VERSION}")
                return None

            camera = save_dict.get("camera", {})

            return SaveData(
                puzzle_path=save_dict["puzzle_path"],
                filled_regions=save_dict["filled_regions"],
                selected_palette=save_dict["selected_palette"],
                selected_region=save_dict["selected_region"],
                camera_x=camera.get("x", 0.0),
                camera_y=camera.get("y", 0.0),
                camera_zoom=camera.get("zoom", 1.0),
            )
        except (OSError, IOError, json.JSONDecodeError, KeyError) as e:
            print(f"Failed to load save: {e}")
            return None

    def has_save(self) -> bool:
        """Check if a save file exists.

        Returns:
            True if save file exists.
        """
        return self._get_save_path().exists()

    def delete_save(self) -> bool:
        """Delete the save file.

        Returns:
            True if deletion succeeded or file didn't exist.
        """
        save_path = self._get_save_path()
        if save_path.exists():
            try:
                save_path.unlink()
                return True
            except OSError as e:
                print(f"Failed to delete save: {e}")
                return False
        return True

    def get_save_puzzle_path(self) -> str | None:
        """Get the puzzle path from save without loading full state.

        Returns:
            Puzzle path string if save exists, None otherwise.
        """
        save_path = self._get_save_path()

        if not save_path.exists():
            return None

        try:
            with open(save_path, "r", encoding="utf-8") as f:
                save_dict = json.load(f)
            return save_dict.get("puzzle_path")
        except (OSError, IOError, json.JSONDecodeError):
            return None


def create_save_data(
    puzzle_path: str,
    filled: list[bool],
    selected_palette: int,
    selected_region: int,
    camera_x: float,
    camera_y: float,
    camera_zoom: float,
) -> SaveData:
    """Helper to create SaveData from game state.

    Args:
        puzzle_path: Path to the puzzle directory (relative to game root).
        filled: List of filled state for each region.
        selected_palette: Currently selected palette index.
        selected_region: Currently selected region ID.
        camera_x: Camera X position in world coordinates.
        camera_y: Camera Y position in world coordinates.
        camera_zoom: Camera zoom level.

    Returns:
        SaveData instance.
    """
    return SaveData(
        puzzle_path=puzzle_path,
        filled_regions=list(filled),  # Copy the list
        selected_palette=selected_palette,
        selected_region=selected_region,
        camera_x=camera_x,
        camera_y=camera_y,
        camera_zoom=camera_zoom,
    )
