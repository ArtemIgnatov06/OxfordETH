from dataclasses import dataclass

@dataclass
class Wallet:
    balance: int

    def can_pay(self, amount: int) -> bool:
        return self.balance >= amount

    def pay(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("amount must be >= 0")
        if self.balance < amount:
            raise ValueError("insufficient funds")
        self.balance -= amount

    def receive(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("amount must be >= 0")
        self.balance += amount
