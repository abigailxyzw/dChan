import hashlib
import html
import re
import urllib.parse
from datetime import datetime

from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

import markdown as md
from .markdown_extensions import ChanExtensions

register = template.Library()


@register.filter(name='markdown')
@stringfilter
def markdown(text, links):
    pattern = re.compile(r'(\n\ {1,4}\n)')  # Match two newlines separated by 1-4 spaces
    text = pattern.sub('\n\n', text)
    text = '\n\n'.join(text.split('\n'))
    text = text.replace('\n\n\n\n', '\n\n&nbsp;\n\n')
    return mark_safe(md.markdown(text, extensions=[ChanExtensions(links)]))


@register.filter(name='reddit_markdown')
@stringfilter
def markdown(text):
    return mark_safe(md.markdown(html.unescape(text), extensions=['mdx_linkify']))


@register.filter(name='get_archive_link')
@stringfilter
def get_archive_link(path):
    parts = path.split('/')[1:]
    new_path = '/'.join(parts)
    return f'https://archive.is/https://8ch.net/{new_path}'


@register.filter(name='get_8kun_link')
@stringfilter
def get_8kun_link(path):
    parts = path.split('/')[1:]
    new_path = '/'.join(parts)
    return f'https://8kun.top/{new_path}'


def hex_to_rgb(hex_):
    try:
        r = int(hex_[:2], 16) / 255
        g = int(hex_[2:4], 16) / 255
        b = int(hex_[4:], 16) / 255
        return r, g, b
    except Exception:
        return 0, 0, 0


def rgb_to_hex(r, g, b):
    return '#{:02x}{:02x}{:02x}'.format(int(r*255), int(g*255), int(b*255))


@register.filter(name='contrast_text')
@stringfilter
def contrast_text(bg_color):
    if bg_color.startswith('#'):
        bg_color = bg_color[1:]
    r, g, b = hex_to_rgb(bg_color)
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    if luminance > 0.65:
        return 'black'
    return 'white'


@register.filter(name='pastelize')
@stringfilter
def pastelize(poster_hash):
    if len(poster_hash) > 6:  # 4chan hash
        hash_bytes = poster_hash.encode()
        hash_obj = hashlib.sha1(hash_bytes)
        poster_hash = hash_obj.hexdigest()[-6:]  # Take last 6 chars
    if poster_hash == '000000':
        return '#000000'
    r, g, b = hex_to_rgb(poster_hash)
    r += (1 - r) / 2
    g += (1 - g) / 2
    b += (1 - b) / 2
    return rgb_to_hex(r, g, b)


@register.filter(name='get_cracked_pass')
@stringfilter
def get_cracked_pass(tripcode):
    tripcode = tripcode.strip('!')
    cracked = {
        'ITPb.qbhqo': 'Matlock',
        'UW.yye1fxo': 'M@tlock!',
        'xowAT4Z3VQ': 'Freed@m-',
        '2jsTvXXmXs': 'F!ghtF!g',
        '4pRcUA0lBE': 'NowC@mes',
        'CbboFOtcZs': 'StoRMkiL',
        'A6yxsPKia.': 'WeAReQ@Q'
    }
    if tripcode in cracked:
        return cracked[tripcode]
    return ''


@register.filter(name='reply_string')
@stringfilter
def reply_string(post_no):
    return f'>>{post_no[-4:]}'


@register.simple_tag
def url_replace(request, field, value):

    dict_ = request.GET.copy()

    dict_[field] = value

    return '?' + urllib.parse.urlencode(dict_)


@register.filter(name='jp_date')
@stringfilter
def jp_date(date):
    if date is None or 'None' in date:
        return None

    date = datetime.fromisoformat(date)
    date_string = date.strftime('%Y/%m/%d %H:%M:%S')
    weekday = date.weekday()
    jp_weekday_map = {
        0: '日',
        1: '月',
        2: '火',
        3: '水',
        4: '木',
        5: '金',
        6: '土'
    }
    date_parts = date_string.split(' ')

    return mark_safe(f'{date_parts[0]} ({jp_weekday_map[weekday]}) {date_parts[1]}')

@register.filter(name='textboard_backlinks')
@stringfilter
def textboard_backlinks(text, path):
    range_pattern = re.compile(r'(?<!>)&gt;&gt;(([0-9]{1,4})([,-][0-9]{1,4})+)')  # Match range e.g. >>123-125,128,130
    reply_pattern = re.compile(r'(?<!>)&gt;&gt;([0-9]{1,4})')  # Match >>1 - >>9999
    path = path[:path.rindex('/')+1]  # Pop anything after the last /
    text = range_pattern.sub(rf'<a href="{path}\1">&gt;&gt;\1</a>', text)
    text = reply_pattern.sub(rf'<a href="{path}#\1">&gt;&gt;\1</a>', text)
    return mark_safe(text)
