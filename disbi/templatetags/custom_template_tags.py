# Django
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def print_none(obj):
    if obj is None:
        return ''
    else:
        return str(obj)

HTML_GLOBAL_ATTRS = ['accesskey',
                     'class',
                     'contenteditable',
                     'contextmenu',
                     'data-*',
                     'dir',
                     'draggable',
                     'dropzone',
                     'hidden',
                     'id',
                     'lang',
                     'spellcheck',
                     'style',
                     'tabindex',
                     'title',
                     'translate']

@register.simple_tag
def nested_dict_as_table(d, make_foot, **kwargs):
    """
    Render a list of dictionries as HTML table with keys as footer and header.
    
    Args:
        d: A list of dictionries. Use an OrderedDict for the table
            to maintain order.
    Keyword Args:
        **kwargs: Valid HTML Global attributes, which will be added 
            to the <table> tag.
    """
    head = ['<th>%s</th>' % headercell for headercell in d[0].keys()]
    if make_foot:
        foot = ['<td>%s</td>' % headercell for headercell in d[0].keys()]
        footer = '''
        <tfoot>
            <tr>
                %s
            </tr>
        </tfoot>
        ''' % '\n'.join(foot)
    body = ['<tr>%s</tr>' % '\n'.join(
                ['<td>%s</td>' % print_none(cell) if not isinstance(cell, list) else 
                 '<td>%s</td>' % ', '.join(cell) for cell in row.values()])
            for row in d]
        
    # Setting the attributes for the <table> tag. 
    table_attrs = []
    for attr in HTML_GLOBAL_ATTRS:
        if kwargs.get(attr):
            table_attrs.append('%s="%s"' % (attr, kwargs[attr]))
    
    table = '''
    <table %s>
        <thead>
            <tr>
                %s
            </tr>
        </thead>
        %s
        <tbody>
            %s
        </tbody>
    </table>
    ''' % (' '.join(table_attrs),
           '\n'.join(head), 
           footer if make_foot else '',
           '\n'.join(body))
    
    return mark_safe(table)
