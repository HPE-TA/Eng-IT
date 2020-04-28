from django.db import models


class Article(models.Model):

    class Meta(object):
        db_table = 'article'

    title = models.CharField(verbose_name='タイトル', max_length=1024)
    body = models.TextField(verbose_name='本文')
    author = models.CharField(verbose_name='著者', max_length=255)
    published_at = models.DateTimeField(verbose_name='公開日時')
    source_url = models.URLField(verbose_name='元記事URL')
    audio_url = models.URLField(verbose_name='音声データURL')
    is_published = models.BooleanField()

    def __str__(self):
        return '{} - {} - {}'.format(
            self.title,
            self.author,
            self.published_at
        )

    def __repr__(self):
        return self.__str__()
