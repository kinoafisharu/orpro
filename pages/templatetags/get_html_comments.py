import re

comment_search_expr = re.compile('\<![ \r\n\t]*(--([^\-]|[\r\n]|-[^\-])*--[ \r\n\t]*)\>')


def get_html_comments(html, expr):
    '''Returns html comments using as space-joined string
    Назначение: выделение в тексте полного описания товара строки для краткого описания на страницу списка товаров.
    Теги для выделения строки: <!-- выделяемый текст -->
    '''
    return ' '.join([x[0][2:-2] for x in expr.findall(html)]).strip()
