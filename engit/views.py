from django.shortcuts import render
from django.shortcuts import redirect
from django.views import View
from django.http import Http404
from django.http.response import JsonResponse
from django.conf import settings
from .models import Article

# import logging
import urllib.request
import requests
import os
import re
from bs4 import BeautifulSoup
from datetime import datetime
from google.cloud import texttospeech
from pydub import AudioSegment

# logger = logging.getLogger(__name__)
# If you need a logging feature for debug purpose, uncomment above.


class IndexView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'engit/index.html')


index = IndexView.as_view()


def collects(request):
    # Collecting Article by NewsAPI
    newsapi_key = os.environ["NEWSAPI_KEY"]
    # TODO: APIの処理に時間がかかるので3件に絞っている
    newsapi_url = (
        'http://newsapi.org/v2/top-headlines?'
        'sources=TechCrunch&'
        'pageSize=3&'
        'apiKey=' + newsapi_key
    )
    articles = requests.get(newsapi_url).json()
    now_time = datetime.utcnow().replace(microsecond=0).isoformat()

    # Set time of before working using time_file like flag file
    time_file = str(os.path.join(settings.STATICFILES_DIRS[0], 'engit', 'time_file'))
    if os.path.isfile(time_file):
        with open(time_file, 'r') as tf:
            lines = tf.readlines()
            oldest = datetime.strptime(lines[0], '%Y-%m-%dT%H:%M:%S')
    else:
        oldest = datetime(1970, 1, 1)

    recorded = []
    for article in articles['articles']:
        publishedat = datetime.strptime(article['publishedAt'], '%Y-%m-%dT%H:%M:%SZ')

        if publishedat <= oldest:
            continue

        # 日本語の記事は除外。
        if 'jp.techcrunch.com' in article['url']:
            continue

        tmp_file_name = os.path.basename(article['url'].rstrip('/'))
        tmp_output_audio = str(os.path.join(settings.TMP_AUDIO_DIR[0], tmp_file_name + '-tmp.wav'))
        audio_file_name = tmp_file_name + '.wav'
        output_audio = str(os.path.join(settings.AUDIOFILES_DIR[0], audio_file_name))

        # crawling (Get Body of an Article)
        html = urllib.request.urlopen(article['url'])
        soup = BeautifulSoup(html, 'html.parser')
        # Get Contents
        contents_html = soup.find("div", {"class": "article-content"})

        # Convert text to audio
        len_paragraph = len(contents_html.find_all(["p", "h2"])) - 1
        tmp_body_html = contents_html.find_all(["p", "h2"])
        body_html = BeautifulSoup('\n\n'.join(str(tb) for tb in tmp_body_html), 'html.parser')

        for n_paragraph, paragraph in enumerate(contents_html.find_all(["p", "h2"]), 1):
            client = texttospeech.TextToSpeechClient()
            input_text = texttospeech.SynthesisInput(text=paragraph.get_text())

            voice = texttospeech.VoiceSelectionParams(
                language_code='en-US',
                ssml_gender=texttospeech.SsmlVoiceGender.FEMALE)

            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16)

            response = client.synthesize_speech(input=input_text, voice=voice, audio_config=audio_config)

            # The response's audio_content is binary.
            with open(tmp_output_audio, 'wb') as out:
                out.write(response.audio_content)

            if n_paragraph == 1:
                print("Title: {}".format(article['title']))
                print("Start Converting")
                audio = AudioSegment.from_file(tmp_output_audio)
            else:
                audio = audio + AudioSegment.from_file(tmp_output_audio)

            print("In progress: ({}/{}) paragraph have finished to convert text to audio.".format(
                str(n_paragraph), str(len_paragraph + 1)))

        # Create a audio file
        audio.export(output_audio)

        # Delete Temporary Audio File
        if os.path.isfile(tmp_output_audio):
            os.remove(tmp_output_audio)
        else:
            print("Error: Temporary Audio File {} not found".format(tmp_output_audio))

        # Update File for production

        # remove img tag
        regex_img = r"<img .*?/>"

        # Add record to Model
        record = Article(
            title=str(article['title']),
            body=re.sub(regex_img, "", str(body_html)),
            author=str(article['author']),
            published_at=datetime.strptime(article['publishedAt'], '%Y-%m-%dT%H:%M:%SZ'),
            source_url=str(article['url']),
            is_published=False
        )
        record.save()
        recorded.append(str(record))

        # Update record with Audio URL
        # TODO: Azure Blob Storage とかに入れるほうが望ましい。
        if str(settings.AUDIOFILES_STORE) == 'LOCAL':
            Article.objects.filter(title=str(article['title'])).update(
                audio_url='engit/audio/' + audio_file_name)
            Article.objects.filter(title=str(article['title'])).update(is_published=True)

    # upate time file
    # TODO: 収集済みの記事の最新時刻のほうがよい。
    with open(time_file, 'w') as tf:
        tf.write(now_time)

    json_res = {
        'newsapi': articles,
        'db_insert': recorded
    }
    return JsonResponse(json_res, json_dumps_params={'indent': 4})


class ArticleListView(View):
    def get(self, request, page=1, *args, **kwargs):
        try:
            page = int(page)
            max_size = settings.MAX_NUM_ARTICLES
            max_chars_body = settings.MAX_CHARS_BODY
        except ValueError:
            raise Http404

        if "keyword" in request.GET:
            keywords = request.GET.get('keyword').split(" ")
            queryset = Article.objects.all().order_by('published_at')
            for keyword in keywords:
                queryset = queryset.filter(body__icontains=keyword)
        else:
            keywords = []
            queryset = Article.objects.all()

        start = (max_size * page) - max_size
        end = (max_size * page)

        context = {
            'next_page': page+1,
            'max_chars_body': max_chars_body,
            'articles': queryset[start:end],
            'keywords': keywords,
        }
        return render(request, 'engit/articles.html', context=context)


article_list = ArticleListView.as_view()


def view404(request, exception):
    return redirect('/')
