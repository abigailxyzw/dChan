import glob
import os

from django.contrib.postgres.search import SearchQuery
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import PageNotAnInteger, EmptyPage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.template import loader
from django.views.generic import ListView
from django_elasticsearch_dsl.search import Search

from dChan import settings
from posts.DSEPaginator import DSEPaginator
from posts.documents import PostDocument
from posts.models import Post, Platform, Drop


def board_links(platform):
    if not platform:
        return None, None
    platform_obj = Platform.objects.get(name=platform)
    if platform == '8kun':
        q_boards = list(Drop.objects.filter(post__platform=platform_obj)
                        .values_list('post__board__name', flat=True)
                        .distinct())
        other_boards = sorted(list(platform_obj.boards.values_list('name', flat=True).distinct()))
        other_boards = sorted([board for board in other_boards if board not in q_boards])
        return q_boards, other_boards

    else:
        return list(platform_obj.boards.values_list('name', flat=True).distinct()), None


def index(request, platform=None, board=None):
    s = PostDocument.search()
    if board:
        threads = s.query('match', is_op=True) \
            .query('match', platform__name=platform) \
            .query('match', board__name=board) \
            .sort('-timestamp')
    elif platform:
        threads = s.query('match', is_op=True) \
            .query('match', platform__name=platform) \
            .sort('-timestamp')
    else:
        threads = s.query('match', is_op=True) \
            .sort('-timestamp')

    page = int(request.GET.get('page', 1))
    results_per_page = 40
    start = (page - 1) * results_per_page
    end = start + results_per_page
    threads = threads[start:end]
    queryset = threads.to_queryset().select_related('platform', 'board')
    response = threads.execute()
    paginator = DSEPaginator(response, results_per_page)
    paginator.set_queryset(queryset)
    page_range = paginator.get_elided_page_range(number=page)

    try:
        page_threads = paginator.page(page)
    except PageNotAnInteger:
        page_threads = paginator.page(1)
    except EmptyPage:
        page_threads = paginator.page(paginator.num_pages)

    boards, other_boards = board_links(platform)

    context = {
        'thread_list': page_threads,
        'platform_name': platform,
        'board_name': board,
        'page_range': page_range,
        'boards_links': boards,
        'other_boards': other_boards
    }

    template = loader.get_template('posts/index.html')
    return HttpResponse(template.render(context, request))


def thread(request, platform='8kun', board=None, thread_id=None):
    context = {}
    poster_hash = request.GET.get('poster_hash')
    try:
        s = PostDocument.search()
        thread_posts = s.query('match', platform__name=platform) \
            .query('match', board__name=board) \
            .query('match', thread_id=thread_id) \
            .sort('post_id') \
            .extra(size=800)

        if poster_hash:
            thread_posts = thread_posts.query('match', poster_hash=poster_hash)

        thread_posts = thread_posts.to_queryset().select_related('drop', 'platform', 'board')

        thread_drops = Drop.objects.filter(post__board__name=board, post__thread_id=thread_id) \
            .select_related('post__platform', 'post__board') \
            .order_by('number')

        drop_links = [(drop_.number, drop_.post.get_post_url()) for drop_ in thread_drops]

        boards, other_boards = board_links(platform)

        context = {
            'posts': thread_posts,
            'platform_name': platform,
            'board_name': board,
            'thread': thread_id,
            'drop_links': drop_links,
            'boards_links': boards,
            'other_boards': other_boards
        }

        if len(thread_posts) == 0:
            raise ObjectDoesNotExist

    except ObjectDoesNotExist:
        # One of the .gets failed, i.e. this thread is not archived
        template = loader.get_template('posts/thread.html')
        return HttpResponse(template.render(context, request), status=404)

    except Exception as e:
        print(e)
        template = loader.get_template('posts/thread.html')
        return HttpResponse(template.render(context, request), status=500)

    template = loader.get_template('posts/thread.html')
    return HttpResponse(template.render(context, request))


def drop(request, drop_no):
    try:
        q_drop = Drop.objects.get(number=drop_no)
    except ObjectDoesNotExist:
        print('Drop is not archived: ', drop_no)
        template = loader.get_template('posts/index.html')
        context = {
            'posts': [],
        }
        return HttpResponse(template.render(context, request))
    return redirect(q_drop.post.get_post_url())


def search_results(request):
    q = request.GET.get('q')
    thread_no = request.GET.get('thread_no')
    subject = request.GET.get('subject')
    name = request.GET.get('name')
    tripcode = request.GET.get('tripcode')
    user_id = request.GET.get('user_id')
    date_start = request.GET.get('date_start')
    date_end = request.GET.get('date_end')
    sort = request.GET.get('sort')
    if (not q or q == '') and not any([thread_no, subject, name, tripcode, user_id, date_start, date_end]):
        return []

    if q and q != '':
        s = Search(index='posts', model=Post).from_dict({
            'query': {
                'simple_query_string': {
                    'query': q,
                    'fields': ['subject^2', 'body'],
                    'default_operator': 'and',
                    'analyze_wildcard': True
                }
            }
        })
        # Setting _model has to be done to use .to_queryset() since we are creating the search from a dict,
        # not PostDocument
        # There is almost definitely a better, less ugly way but this works
        s._model = Post
    else:
        s = PostDocument.search()

    if thread_no:
        s = s.query('match', thread_id=thread_no)
    if subject:
        s = s.query('match', subject=subject)
    if name:
        s = s.query('match', author=name)
    if tripcode:
        s = s.query('match', tripcode=tripcode)
    if user_id:
        s = s.query('match', poster_hash=user_id)
    if date_start:
        s = s.query('range', timestamp={'gte': date_start})
    if date_end:
        s = s.query('range', timestamp={'lte': date_end})
    if sort:
        if sort == 'newest':
            s = s.sort('-timestamp')
        if sort == 'oldest':
            s = s.sort('timestamp')
        if sort == 'relevance':
            # Already sorted by relevance
            pass
    else:
        s = s.sort('-timestamp')

    page = int(request.GET.get('page', 1))
    results_per_page = 50
    start = (page - 1) * results_per_page
    end = start + results_per_page
    results = s[start:end]
    queryset = results.to_queryset().select_related('platform', 'board')
    response = results.execute()
    paginator = DSEPaginator(response, results_per_page)
    paginator.set_queryset(queryset)
    page_range = paginator.get_elided_page_range(number=page)

    try:
        page_results = paginator.page(page)
    except PageNotAnInteger:
        page_results = paginator.page(1)
    except EmptyPage:
        page_results = paginator.page(paginator.num_pages)

    context = {
        'results': page_results,
        'page_range': page_range,
        'hits': s.count()
    }

    template = loader.get_template('posts/search_results.html')
    return HttpResponse(template.render(context, request))


class AdvancedSearch(ListView):
    model = Post
    template_name = 'posts/advanced_search.html'
    context_object_name = 'results'

    def get_queryset(self):
        query = SearchQuery(self.request.GET.get('q'))
        results = Post.objects.filter(search_vector=query)[:100]
        return results

    def get_context_data(self, **kwargs):
        context = super(AdvancedSearch, self).get_context_data(**kwargs)
        boards = Post.objects.values_list('platform', 'board').distinct()
        context['boards'] = boards
        return context


def first_to_say(request, phrase):
    s = PostDocument.search()
    s = s.query('match_phrase', body=phrase)
    results = s.sort('timestamp').extra(size=100).to_queryset()
    template = loader.get_template('posts/thread.html')
    return HttpResponse(template.render({'posts': results}, request))


def timeseries_from_keywords(request):
    keywords = request.GET.get('keywords')
    agg = request.GET.get('agg')

    s = Search(index='posts').from_dict({
        'query': {
            'range': {
                'timestamp': {
                    'gte': '2017-10-28'
                }
            }
        },
        'aggs': {
            "posts_over_time": {
                "date_histogram": {
                    "field": "timestamp",
                    "calendar_interval": agg
                },
                'aggs': {
                    'total': {
                        'value_count': {'field': '_id'}
                    },
                    'keywords_filter': {
                        'filter': {
                            'bool': {
                                'must': [
                                    {
                                        'range': {
                                            'timestamp': {
                                                'gte': '2017-10-28'
                                            }
                                        }
                                    },
                                    {
                                        'query_string': {
                                            'query': keywords,
                                            'default_field': 'body',
                                            'default_operator': 'AND',
                                            'analyze_wildcard': True
                                        },
                                    },
                                ]
                            }
                        },
                    },
                    'per_mille': {
                        'bucket_script': {
                            'buckets_path': {
                                'matches': 'keywords_filter._count',
                                'total': 'total',
                            },
                            'script': 'params.matches / params.total * 1000'
                        }
                    }
                },
            },
        },
    })
    results = s.execute().aggregations.to_dict()
    return JsonResponse({'data': results})


def timeseries_frontend(request):
    js_chunks = glob.glob(os.path.join(settings.REACT_APP_DIR, 'build', 'static', 'js', '*.chunk.js'))
    template = loader.get_template('posts/timeseries.html')
    return HttpResponse(template.render({'js_chunks': js_chunks}, request))
