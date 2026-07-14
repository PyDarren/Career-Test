# 画己职测 — 分页类

from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """标准分页类：page_size=20，支持前端通过 page_size 参数自定义，
    最大不超过 100。"""

    page_size: int = 20
    page_size_query_param: str = "page_size"
    max_page_size: int = 100
