from api.core.errors import ConflictError, ForbiddenError, NotFoundError, UnavailableError


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


class NotAnActor(ForbiddenError):
    def __init__(self, user_id):
        super().__init__('not_an_actor', f'User {user_id} is not a supply-chain actor.')


class WineryOnly(ForbiddenError):
    def __init__(self):
        super().__init__('winery_only', 'Only winery actors can register wines.')


class NotTheProducer(ForbiddenError):
    def __init__(self, wine_id):
        super().__init__('producer_only', f'Only the producer can retire wine {wine_id}.')


class LegacyWine(ConflictError):
    def __init__(self, wine_id):
        super().__init__('legacy_wine', f'Wine {wine_id} was registered before the contract and cannot move on chain.')


class LedgerRuleViolation(ConflictError):
    """The contract rejected the operation because one of its rules does not hold."""

    def __init__(self, rule):
        super().__init__(rule.replace(' ', '_'), f'Rejected by the traceability contract: {rule}.')
        self.rule = rule


class ActorNotFound(NotFoundError):
    def __init__(self, actor_id):
        super().__init__('actor_not_found', f'Actor {actor_id} does not exist.')


class ActorRevoked(ForbiddenError):
    def __init__(self, actor_id):
        super().__init__('actor_revoked', f'Actor {actor_id} was revoked and can no longer operate.')


class ActorAlreadyRevoked(ConflictError):
    def __init__(self, actor_id):
        super().__init__('actor_already_revoked', f'Actor {actor_id} is already revoked.')


class MemberAlreadyExists(ConflictError):
    def __init__(self, email):
        super().__init__('member_already_exists', f'An account with {email} already exists.')
