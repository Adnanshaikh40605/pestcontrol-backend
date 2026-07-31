from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle


class CustomerAuthAnonThrottle(AnonRateThrottle):
    scope = 'customer_auth'


class CustomerRateThrottle(SimpleRateThrottle):
    scope = 'customer'

    def get_cache_key(self, request, view):
        account = getattr(request, 'customer', None)
        if account is None:
            return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}
        return self.cache_format % {'scope': self.scope, 'ident': f'customer-{account.id}'}
