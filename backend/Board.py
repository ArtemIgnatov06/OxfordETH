from enum import Enum

class CellType(Enum):
    START = "START"
    PROPERTY = "PROPERTY"
    JAIL = "JAIL"
    GO_TO_JAIL = "GO_TO_JAIL"
    SERVER_DOWN = "SERVER_DOWN"
    BUG = "BUG"
    CHANCE = "CHANCE"
    GASFEES = "GASFEES"



class AssetFamily(Enum):
    BTC = "BTC"
    ETH = "ETH"
    SOL = "SOL"
    BNB = "BNB"
    MEME = "MEME"

class Asset:
    def __init__(self, asset_id: str, family: AssetFamily, tier: int):
        self.id = asset_id          # e.g. "BTC1", "ETH2", "MEME1"
        self.family = family        # BTC / ETH / SOL / MEME
        self.tier = tier            # 1, 2, 3 (MEME can still use tier=1,2)

    def __repr__(self):
        return f"Asset(id={self.id}, family={self.family.value}, tier={self.tier})"

class Cell:
    def __init__(self, index: int, cell_type: CellType, asset: Asset | None = None):
        self.index = index
        self.type = cell_type
        self.asset = asset  # Only for PROPERTY cells

    def __repr__(self):
        if self.type == CellType.PROPERTY:
            return f"Cell({self.index}, PROPERTY, {self.asset.id})"
        return f"Cell({self.index}, {self.type.value})"


class BoardGame:
    def __init__(self):
        self.cells: list[Cell] = []
        self._initialize_board()

    def _initialize_board(self) -> None:
        assets = self._create_assets()
        idx = 0

        # START
        self.cells.append(Cell(idx, CellType.START))
        idx += 1

        # BTC family
        self.cells.append(Cell(idx, CellType.PROPERTY, assets["BTC1"])); idx += 1
        self.cells.append(Cell(idx, CellType.PROPERTY, assets["BTC2"])); idx += 1
        self.cells.append(Cell(idx, CellType.PROPERTY, assets["BTC3"])); idx += 1

        # CHANCE #1
        self.cells.append(Cell(idx, CellType.CHANCE))
        idx += 1

        # SERVER DOWN
        self.cells.append(Cell(idx, CellType.SERVER_DOWN))
        idx += 1

        self.cells.append(Cell(idx, CellType.GASFEES))
        idx += 1

        # ETH family
        self.cells.append(Cell(idx, CellType.PROPERTY, assets["ETH1"])); idx += 1
        self.cells.append(Cell(idx, CellType.PROPERTY, assets["ETH2"])); idx += 1
        self.cells.append(Cell(idx, CellType.PROPERTY, assets["ETH3"])); idx += 1

        # CHANCE #2
        self.cells.append(Cell(idx, CellType.CHANCE))
        idx += 1

        # BUG → GO TO JAIL
        self.cells.append(Cell(idx, CellType.BUG))
        idx += 1

        # JAIL
        self.cells.append(Cell(idx, CellType.JAIL))
        idx += 1

        # CHANCE #3
        self.cells.append(Cell(idx, CellType.CHANCE))
        idx += 1

        # SOL family
        self.cells.append(Cell(idx, CellType.PROPERTY, assets["SOL1"])); idx += 1
        self.cells.append(Cell(idx, CellType.PROPERTY, assets["SOL2"])); idx += 1
        self.cells.append(Cell(idx, CellType.PROPERTY, assets["SOL3"])); idx += 1

        self.cells.append(Cell(idx, CellType.PROPERTY, assets["BNB1"]));
        idx += 1
        self.cells.append(Cell(idx, CellType.PROPERTY, assets["BNB2"]));
        idx += 1
        self.cells.append(Cell(idx, CellType.PROPERTY, assets["BNB3"]));
        idx += 1

        # MEME coins
        self.cells.append(Cell(idx, CellType.PROPERTY, assets["MEME1"])); idx += 1
        self.cells.append(Cell(idx, CellType.PROPERTY, assets["MEME2"])); idx += 1

        # CHANCE #4
        self.cells.append(Cell(idx, CellType.CHANCE))
        idx += 1

        # GO TO JAIL
        self.cells.append(Cell(idx, CellType.GO_TO_JAIL))


    def _create_assets(self) -> dict[str, Asset]:
        return {
            "BTC1": Asset("BTC1", AssetFamily.BTC, 1),
            "BTC2": Asset("BTC2", AssetFamily.BTC, 2),
            "BTC3": Asset("BTC3", AssetFamily.BTC, 3),

            "ETH1": Asset("ETH1", AssetFamily.ETH, 1),
            "ETH2": Asset("ETH2", AssetFamily.ETH, 2),
            "ETH3": Asset("ETH3", AssetFamily.ETH, 3),

            "SOL1": Asset("SOL1", AssetFamily.SOL, 1),
            "SOL2": Asset("SOL2", AssetFamily.SOL, 2),
            "SOL3": Asset("SOL3", AssetFamily.SOL, 3),

            "BNB1": Asset("BNB1", AssetFamily.BNB, 1),
            "BNB2": Asset("BNB2", AssetFamily.BNB, 2),
            "BNB3": Asset("BNB3", AssetFamily.BNB, 3),

            "MEME1": Asset("MEME1", AssetFamily.MEME, 1),
            "MEME2": Asset("MEME2", AssetFamily.MEME, 2),
        }

    def get_cell(self, position: int) -> Cell:
        """Wrap-around access (board is circular)."""
        return self.cells[position % len(self.cells)]

    @property
    def size(self) -> int:
        return len(self.cells)

if __name__ == "__main__":
    board = BoardGame()

    print("Board size:", board.size)
    for cell in board.cells:
        print(cell)

    print("Cell at position 20 (wrap):", board.get_cell(20))
