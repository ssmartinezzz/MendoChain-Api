from api.core.errors import ConflictError, NotFoundError, UnavailableError


class WineNotFound(NotFoundError):
    def __init__(self, wine_id):
        super().__init__('wine_not_found', f'Wine {wine_id} does not exist.')


class TransactionNotFound(NotFoundError):
    def __init__(self, transaction_id):
        super().__init__('transaction_not_found', f'Transaction {transaction_id} does not exist.')


class LedgerUnavailable(UnavailableError):
    def __init__(self, reason):
        super().__init__('ledger_unavailable', 'The movement could not be recorded on the ledger.')
        self.reason = reason


class ActorAlreadyRegistered(ConflictError):
    def __init__(self, user_id):
        super().__init__('actor_already_registered', f'User {user_id} is already a supply-chain actor.')
