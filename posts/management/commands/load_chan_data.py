from csv import DictReader
from django.core.management import BaseCommand
from tqdm import tqdm

from posts.models import Post


def parse_formatting(html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')

    # Process green text
    for result in soup.find_all(attrs={'class': 'quote'}):
        result.insert(0, '> ')

    # Process red text
    for result in soup.find_all(attrs={'class': 'heading'}):
        result.insert_before('==')
        result.insert_after('==')

    # Process bold text
    for result in soup.find_all('strong'):
        result.insert_before("'''")
        result.insert_after("'''")

    # Process italic text
    for result in soup.find_all('em'):
        if result.get_text() != '//':  # For some reason, the // in URLs is wrapped with <em />
            result.insert_before("''")
            result.insert_after("''")

    # Process underlined text
    for result in soup.find_all('u'):
        result.insert_before("__")
        result.insert_after("__")

    # Process strikethrough text
    for result in soup.find_all('s'):
        result.insert_before("~~")
        result.insert_after("~~")

    # Process spoiler text
    for result in soup.find_all(attrs={'class': 'spoiler'}):
        result.insert_before("**")
        result.insert_after("**")

    final_text = '\n'.join([line.get_text() for line in soup.find_all(attrs={'class': 'body-line'})])
    return final_text


def split_list(lst, n):
    from itertools import islice
    lst = iter(lst)
    result = iter(lambda: tuple(islice(lst, n)), ())
    return list(result)


class Command(BaseCommand):
    help = "Load data from CSV files scraped from Chan data. Expects three files, 4chan.csv, 8chan.csv, 8kun.csv"

    def handle(self, *args, **options):
        if Post.objects.exists():
            delete = input('Data already in database. Delete all data first? (y/n)\n')
            if delete == 'y':
                Post.objects.all().delete()

        for platform in ['4chan', '8chan', '8kun']:
            print(f'Loading {platform} data...')
            try:
                reader = DictReader(open(f'{platform}.csv'))
                row_count = sum(1 for row in reader)
                new_posts = []
                for row in tqdm(DictReader(open(f'{platform}.csv')), total=row_count):
                    post = Post(platform=platform, board=row['board'], thread_id=row['thread_no'],
                                post_id=row['post_no'], author=row['name'], subject=row['subject'],
                                body=row['body_text'], timestamp=row['timestamp'], tripcode=row['tripcode'],
                                is_op=(row['post_no'] == row['thread_no']))
                    new_posts.append(post)
                    if len(new_posts) >= 10000:
                        Post.objects.bulk_create(new_posts)
                        new_posts = []

                Post.objects.bulk_create(new_posts)

            except Exception as e:
                print(f'Could not load {platform} data.', e)

        print('Done!')
