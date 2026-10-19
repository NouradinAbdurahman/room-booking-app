from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """Page-number pagination for every list (ADR 0006): default and maximum page size 100."""

    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 100
