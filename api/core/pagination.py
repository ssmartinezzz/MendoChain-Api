from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    """Page number pagination; the size comes from REST_FRAMEWORK['PAGE_SIZE']."""
