from sqlalchemy.orm import Session

from app.database.models import Symbol


class SymbolService:
    def __init__(self, db: Session):
        self.db = db

    def get_all_symbols(self):
        return self.db.query(Symbol).all()

    def get_symbol(self, symbol_id: int):
        return (
            self.db.query(Symbol)
            .filter(Symbol.id == symbol_id)
            .first()
        )

    def get_symbol_by_ticker(self, ticker: str):
        return (
            self.db.query(Symbol)
            .filter(Symbol.ticker == ticker)
            .first()
        )

    def create_symbol(self, ticker, display_name, asset_type, is_active=True):
        symbol = Symbol(
            ticker=ticker,
            display_name=display_name,
            asset_type=asset_type,
            is_active=is_active,
        )

        self.db.add(symbol)
        self.db.commit()
        self.db.refresh(symbol)

        return symbol

    def update_symbol(self, symbol_id, ticker, display_name, asset_type, is_active):
        symbol = self.get_symbol(symbol_id)

        if not symbol:
            return None

        symbol.ticker = ticker
        symbol.display_name = display_name
        symbol.asset_type = asset_type
        symbol.is_active = is_active

        self.db.commit()
        self.db.refresh(symbol)

        return symbol

    def delete_symbol(self, symbol_id):
        symbol = self.get_symbol(symbol_id)

        if not symbol:
            return False

        self.db.delete(symbol)
        self.db.commit()

        return True
