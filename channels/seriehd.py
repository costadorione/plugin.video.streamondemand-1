# -*- coding: utf-8 -*-
# ------------------------------------------------------------
# streamondemand.- XBMC Plugin
# Canal para seriehd - based on guardaserie channel
# http://blog.tvalacarta.info/plugin-xbmc/streamondemand.
# ------------------------------------------------------------
import base64
import re
import time
import urllib
import urlparse

from core import config
from core import logger
from core import scrapertools
from core.item import Item

__channel__ = "seriehd"
__category__ = "S"
__type__ = "generic"
__title__ = "Serie HD"
__language__ = "IT"

host = "http://www.seriehd.org"

headers = [
    ['User-Agent', 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:44.0) Gecko/20100101 Firefox/44.0'],
    ['Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'],
    ['Accept-Encoding', 'gzip, deflate'],
    ['Referer', host],
    ['Cache-Control', 'max-age=0']
]


def isGeneric():
    return True


def mainlist(item):
    logger.info("[seriehd.py] mainlist")

    itemlist = [Item(channel=__channel__,
                     action="fichas",
                     title="[COLOR azure]Serie TV[/COLOR]",
                     url=host + "/serie-tv-streaming/",
                     thumbnail="http://i.imgur.com/rO0ggX2.png"),
                Item(channel=__channel__,
                     action="sottomenu",
                     title="[COLOR orange]Sottomenu...[/COLOR]",
                     url=host,
                     thumbnail="http://i37.photobucket.com/albums/e88/xzener/NewIcons.png"),
                Item(channel=__channel__,
                     action="search",
                     title="[COLOR green]Cerca...[/COLOR]",
                     thumbnail="http://dc467.4shared.com/img/fEbJqOum/s7/13feaf0c8c0/Search")]

    return itemlist


def search(item, texto):
    logger.info("[seriehd.py] search")

    item.url = host + "/?s=" + texto

    try:
        return fichas(item)

    # Se captura la excepción, para no interrumpir al buscador global si un canal falla.
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []


def sottomenu(item):
    logger.info("[seriehd.py] sottomenu")
    itemlist = []

    # data = anti_cloudflare(item.url)
    data = scrapertools.cache_page(item.url, headers=headers)

    print data

    patron = '<a href="([^"]+)">([^<]+)</a>'

    matches = re.compile(patron, re.DOTALL).findall(data)

    for scrapedurl, scrapedtitle in matches:
        itemlist.append(
            Item(channel=__channel__,
                 action="fichas",
                 title=scrapedtitle,
                 url=scrapedurl))

    # Elimina 'Serie TV' de la lista de 'sottomenu'
    itemlist.pop(0)

    return itemlist


def fichas(item):
    logger.info("[seriehd.py] fichas")
    itemlist = []

    data = anti_cloudflare(item.url)

    # ------------------------------------------------
    cookies = ""
    matches = re.compile('(.seriehd.org.*?)\n', re.DOTALL).findall(config.get_cookie_data())
    for cookie in matches:
        name = cookie.split('\t')[5]
        value = cookie.split('\t')[6]
        cookies += name + "=" + value + ";"
    headers.append(['Cookie', cookies[:-1]])
    import urllib
    _headers = urllib.urlencode(dict(headers))
    # ------------------------------------------------

    patron = '<h2>(.*?)</h2>\s*'
    patron += '<img src="([^"]+)" alt="[^"]*"/>\s*'
    patron += '<A HREF="([^"]+)">'

    matches = re.compile(patron, re.DOTALL).findall(data)

    for scrapedtitle, scrapedthumbnail, scrapedurl in matches:
        scrapedthumbnail += "|" + _headers
        scrapedtitle = scrapertools.decodeHtmlentities(scrapedtitle).strip()

        tmdbtitle = scrapedtitle.split("(")[0]
        try:
            plot, fanart, poster, extrameta = info(tmdbtitle)

            itemlist.append(
                Item(channel=__channel__,
                     thumbnail=poster,
                     fanart=fanart if fanart != "" else poster,
                     extrameta=extrameta,
                     plot=str(plot),
                     action="episodios",
                     title="[COLOR azure]" + scrapedtitle + "[/COLOR]",
                     url=scrapedurl,
                     fulltitle=scrapedtitle,
                     show=scrapedtitle,
                     folder=True))
        except:
            itemlist.append(
                Item(channel=__channel__,
                     action="episodios",
                     title="[COLOR azure]" + scrapedtitle + "[/COLOR]",
                     fulltitle=scrapedtitle,
                     url=scrapedurl,
                     show=scrapedtitle,
                     thumbnail=scrapedthumbnail))

    patron = "<span class='current'>\d+</span><a rel='nofollow' class='page larger' href='([^']+)'>\d+</a>"
    next_page = scrapertools.find_single_match(data, patron)
    if next_page != "":
        itemlist.append(
            Item(channel=__channel__,
                 action="fichas",
                 title="[COLOR orange]Successivo>>[/COLOR]",
                 url=next_page))

    return itemlist


def episodios(item):
    logger.info("[seriehd.py] episodios")
    itemlist = []

    data = anti_cloudflare(item.url)

    patron = r'<iframe width=".+?" height=".+?" src="([^"]+)" allowfullscreen frameborder="0">'
    url = scrapertools.find_single_match(data, patron).replace("?seriehd", "")

    data = scrapertools.cache_page(url).replace('\n', '').replace(' class="active"', '')

    section_stagione = scrapertools.find_single_match(data, '<h3>STAGIONE</h3><ul>(.*?)</ul>')
    patron = '<li[^>]+><a href="([^"]+)">(\d)<'
    seasons = re.compile(patron, re.DOTALL).findall(section_stagione)

    for scrapedseason_url, scrapedseason in seasons:

        season_url = urlparse.urljoin(url, scrapedseason_url)
        data = scrapertools.cache_page(season_url).replace('\n', '').replace(' class="active"', '')

        section_episodio = scrapertools.find_single_match(data, '<h3>EPISODIO</h3><ul>(.*?)</ul>')
        patron = '<li><a href="([^"]+)">(\d+)<'
        episodes = re.compile(patron, re.DOTALL).findall(section_episodio)

        for scrapedepisode_url, scrapedepisode in episodes:
            episode_url = urlparse.urljoin(url, scrapedepisode_url)

            title = scrapedseason + "x" + scrapedepisode.zfill(2)

            itemlist.append(
                Item(channel=__channel__,
                     action="findvideos",
                     title=title,
                     url=episode_url,
                     fulltitle=item.fulltitle,
                     show=item.show,
                     thumbnail=item.thumbnail))

    if config.get_library_support() and len(itemlist) != 0:
        itemlist.append(
            Item(channel=__channel__,
                 title=item.title + " (Add Serie to Library)",
                 url=item.url,
                 action="add_serie_to_library",
                 extra="episodios",
                 show=item.show))
        itemlist.append(
            Item(channel=item.channel,
                 title="Scarica tutti gli episodi della serie",
                 url=item.url,
                 action="download_all_episodes",
                 extra="episodios",
                 show=item.show))

    return itemlist


def findvideos(item):
    logger.info("[seriehd1.py] findvideos")
    itemlist = []

    data = scrapertools.cache_page(item.url).replace('\n', '')

    patron = '<iframe id="iframeVid" width=".+?" height=".+?" src="([^"]+)" allowfullscreen="">'
    url = scrapertools.find_single_match(data, patron)

    if 'hdpass' in url:
        data = scrapertools.cache_page(url, headers=headers).replace('\n', '').replace('> <', '><')

        # patron = '<form method="get" action="">'
        # patron += '<input type="hidden" name="([^"]*)" value="([^"]*)"/>'
        # patron += '<input type="hidden" name="([^"]*)" value="([^"]*)"/>'
        # patron += '<input type="hidden" name="([^"]*)" value="([^"]*)"/>'
        # patron += '<input type="hidden" name="([^"]*)" value="([^"]*)"/>'
        # patron += '<input type="submit" class="[^"]*" name="([^"]*)" value="([^"]*)"/>'
        # patron += '</form>'
        #
        # for name1, val1, name2, val2, name3, val3, name4, val4, name5, val5 in re.compile(patron).findall(data):
        #
        #     get_data = '%s=%s&%s=%s&%s=%s&%s=%s&%s=%s' % (
        #         name1, val1, name2, val2, name3, val3, name4, val4, name5, val5)
        #
        #     tmp_data = scrapertools.cache_page('http://hdpass.xyz/film.php?' + get_data, headers=headers)

        patron = r'<input type="hidden" name="urlEmbed" data-mirror="([^"]+)" id="urlEmbed" value="([^"]+)"/>'

        for media_label, media_url in re.compile(patron).findall(data):
            media_label = scrapertools.decodeHtmlentities(media_label.replace("hosting", "hdload"))

            itemlist.append(
                Item(channel=__channel__,
                     server=media_label,
                     action="play",
                     title=' - [Player]' if media_label == '' else ' - [Player @%s]' % media_label,
                     url=url_decode(media_url),
                     folder=False))

    return itemlist


def parseJSString(s):
    try:
        offset = 1 if s[0] == '+' else 0
        val = int(eval(s.replace('!+[]', '1').replace('!![]', '1').replace('[]', '0').replace('(', 'str(')[offset:]))
        return val
    except:
        pass


def anti_cloudflare(url):
    result = scrapertools.cache_page(url, headers=headers)
    try:
        jschl = re.compile('name="jschl_vc" value="(.+?)"/>').findall(result)[0]
        init = re.compile('setTimeout\(function\(\){\s*.*?.*:(.*?)};').findall(result)[0]
        builder = re.compile(r"challenge-form\'\);\s*(.*)a.v").findall(result)[0]
        decrypt_val = parseJSString(init)
        lines = builder.split(';')

        for line in lines:
            if len(line) > 0 and '=' in line:
                sections = line.split('=')
                line_val = parseJSString(sections[1])
                decrypt_val = int(eval(str(decrypt_val) + sections[0][-1] + str(line_val)))

        urlsplit = urlparse.urlsplit(url)
        h = urlsplit.netloc
        s = urlsplit.scheme

        answer = decrypt_val + len(h)

        query = '%s/cdn-cgi/l/chk_jschl?jschl_vc=%s&jschl_answer=%s' % (url, jschl, answer)

        if 'type="hidden" name="pass"' in result:
            passval = re.compile('name="pass" value="(.*?)"').findall(result)[0]
            query = '%s/cdn-cgi/l/chk_jschl?pass=%s&jschl_vc=%s&jschl_answer=%s' % (s + '://' + h, urllib.quote_plus(passval), jschl, answer)
            time.sleep(5)

        scrapertools.get_headers_from_response(query, headers=headers)
        return scrapertools.cache_page(url, headers=headers)
    except:
        return result


def url_decode(url_enc):
    lenght = len(url_enc)
    if lenght % 2 == 0:
        len2 = lenght / 2
        first = url_enc[0:len2]
        last = url_enc[len2:lenght]
        url_enc = last + first
        reverse = url_enc[::-1]
        return base64.b64decode(reverse)

    last_car = url_enc[lenght - 1]
    url_enc[lenght - 1] = ' '
    url_enc = url_enc.strip()
    len1 = len(url_enc)
    len2 = len1 / 2
    first = url_enc[0:len2]
    last = url_enc[len2:len1]
    url_enc = last + first
    reverse = url_enc[::-1]
    reverse = reverse + last_car
    return base64.b64decode(reverse)


def info(title):
    logger.info("streamondemand.seriehd info")
    try:
        from core.tmdb import Tmdb
        oTmdb = Tmdb(texto_buscado=title, tipo="tv", include_adult="false", idioma_busqueda="it")
        if oTmdb.total_results > 0:
            extrameta = {"Year": oTmdb.result["release_date"][:4],
                         "Genre": ", ".join(oTmdb.result["genres"]),
                         "Rating": float(oTmdb.result["vote_average"])}
            fanart = oTmdb.get_backdrop()
            poster = oTmdb.get_poster()
            plot = oTmdb.get_sinopsis()
            return plot, fanart, poster, extrameta
    except:
        pass
