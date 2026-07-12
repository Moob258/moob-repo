# -*- coding: utf-8 -*-
import sys
import os
import re
import urllib.parse
import urllib.request
import html as html_module
import base64

import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc
import xbmcvfs

addon = xbmcaddon.Addon()
addon_handle = int(sys.argv[1])
base_url = sys.argv[0]
args = urllib.parse.parse_qs(sys.argv[2][1:])

BASE_URL = 'https://cuevana3i.you'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}
XOR_KEY = 'a45f04ce-2394-47c3-b718-0ecd97ce51d6'
TOKEN_SERVERS = {'1': 'https://tiktokshopping.xyz/v/', '2': 'https://filemoon.sx/e/', '3': 'https://martinshop.xyz/e/', '4': 'https://dood.li/e/'}


def fetch(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        xbmc.log('[Moob] Error: ' + str(e), xbmc.LOGERROR)
        return ''


def build_url(query):
    return base_url + '?' + urllib.parse.urlencode(query)


def dec(text):
    return html_module.unescape(text)


def parse_items(html):
    items = []
    for m in re.finditer(r'<div class="movie-item"><a href="([^"]+)"[^>]*>(.*?)</a></div>', html, re.DOTALL):
        href = m.group(1)
        inner = m.group(2)
        title_m = re.search(r'<div class="item-detail"><p>([^<]+)</p>', inner)
        title = dec(title_m.group(1).strip()) if title_m else href.split('/')[-1].replace('-', ' ').title()
        poster_m = re.search(r'<img[^>]*src=(https?://image\.tmdb\.org[^"\'>\s]+)', inner)
        poster = poster_m.group(1).replace('/w200/', '/w500/') if poster_m else ''
        year_m = re.search(r'<span class="year[^"]*">(\d{4})', inner)
        year = int(year_m.group(1)) if year_m else 0
        item_type = 'movie' if '/pelicula/' in href else 'tvshow'
        items.append({'title': title, 'url': href, 'poster': poster, 'year': year, 'type': item_type})
    return items


def add_item(title, url, poster='', info=None, is_folder=True, is_playable=False, context_menu=None):
    li = xbmcgui.ListItem(title)
    if poster:
        li.setArt({'poster': poster, 'thumb': poster, 'fanart': poster})
    if info:
        li.setInfo('video', info)
    if is_playable:
        li.setProperty('IsPlayable', 'true')
    if context_menu:
        li.addContextMenuItems(context_menu)
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=is_folder)


# ===================== URL RESOLVER =====================
def decode_server_url(server_url):
    if 'tungtungsahur.cuevana3i.you' not in server_url:
        return server_url
    parsed = urllib.parse.urlparse(server_url)
    params = urllib.parse.parse_qs(parsed.query)
    if 'token' in params:
        token = params['token'][0]
        key = token[0]
        if key in TOKEN_SERVERS:
            try:
                decoded = base64.b64decode(token[1:]).decode()
                decrypted = ''
                for i in range(len(decoded)):
                    decrypted += chr(ord(decoded[i]) ^ ord(XOR_KEY[i % len(XOR_KEY)]))
                return TOKEN_SERVERS[key] + decrypted
            except Exception:
                pass
    elif 'v' in params:
        try:
            return base64.b64decode(params['v'][0]).decode()
        except Exception:
            pass
    return server_url


def resolve_video_url(embed_url):
    html = fetch(embed_url)
    if not html:
        return None
    m3u8 = re.findall(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html)
    if m3u8:
        return m3u8[0]
    mp4 = re.findall(r'(https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*)', html)
    if mp4:
        return mp4[0]
    packed = re.search(r"eval\(function\(p,a,c,k,e,d\)\{", html)
    if packed:
        try:
            start = html.index("eval(function(p,a,c,k,e,d)")
            depth = 0
            end = start
            for idx in range(start, min(start + 100000, len(html))):
                if html[idx] == '(':
                    depth += 1
                elif html[idx] == ')':
                    depth -= 1
                    if depth == 0:
                        end = idx + 1
                        break
            packed_code = html[start:end]
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'resources', 'lib'))
            import jsbeautifier
            unpacked = jsbeautifier.beautify(packed_code)
            if unpacked:
                urls = re.findall(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', unpacked)
                if urls:
                    return urls[0]
                urls = re.findall(r'(https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*)', unpacked)
                if urls:
                    return urls[0]
                links_m = re.search(r'var\s+links\s*=\s*\{([^}]+)\}', unpacked)
                if links_m:
                    for url in re.findall(r'"(https?://[^"]+)"', links_m.group(1)):
                        if '.m3u8' in url:
                            return url
        except Exception as e:
            xbmc.log('[Moob] Unpack error: ' + str(e), xbmc.LOGERROR)
    iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)', html)
    for iframe_url in iframes:
        if iframe_url.startswith('//'):
            iframe_url = 'https:' + iframe_url
        if iframe_url.startswith('http'):
            result = resolve_video_url(iframe_url)
            if result:
                return result
    return None


GENRES = {
    'Accion': 'accion', 'Animacion': 'animacion', 'Anime': 'anime',
    'Aventura': 'aventura', 'Belica': 'belica', 'Ciencia Ficcion': 'ciencia-ficcion',
    'Comedia': 'comedia', 'Crimen': 'crimen', 'Documental': 'documental',
    'Drama': 'drama', 'Familia': 'familia', 'Fantasia': 'fantasia',
    'Historia': 'historia', 'Infantil': 'infantil', 'Misterio': 'misterio',
    'Musica': 'musica', 'Noticias': 'news', 'Pelicula de TV': 'pelicula-de-tv',
    'Politica': 'politica', 'Reality': 'reality', 'Romance': 'romance',
    'Suspenso': 'suspenso', 'Telenovela': 'telenovela', 'Terror': 'terror',
    'Western': 'western'
}


# ===================== MENU PRINCIPAL =====================
def menu_principal():
    add_item('[B]Peliculas[/B]', build_url({'action': 'peliculas'}))
    add_item('[B]Peliculas Destacadas[/B]', build_url({'action': 'peliculas_destacadas'}))
    add_item('[B]Series[/B]', build_url({'action': 'series'}))
    add_item('[B]Series Destacadas[/B]', build_url({'action': 'series_destacadas'}))
    add_item('[B]Generos Peliculas[/B]', build_url({'action': 'generos_peliculas'}))
    add_item('[B]Generos Series[/B]', build_url({'action': 'generos_series'}))
    add_item('[B]Busqueda[/B]', build_url({'action': 'busqueda'}))
    xbmcplugin.endOfDirectory(addon_handle)


# ===================== GENEROS =====================
def show_generos_peliculas():
    for display, url_val in GENRES.items():
        add_item(display, build_url({'action': 'peliculas', 'genero': url_val}))
    xbmcplugin.endOfDirectory(addon_handle)


def show_generos_series():
    for display, url_val in GENRES.items():
        add_item(display, build_url({'action': 'series', 'genero': url_val}))
    xbmcplugin.endOfDirectory(addon_handle)


# ===================== PELICULAS =====================
def show_peliculas(page=1, genero=''):
    url = BASE_URL + '/peliculas'
    params = []
    if genero:
        params.append('genero=' + urllib.parse.quote(genero))
    if page > 1:
        params.append('page=' + str(page))
    if params:
        url += '?' + '&'.join(params)
    html = fetch(url)
    if not html:
        add_item('Error al cargar', '')
        xbmcplugin.endOfDirectory(addon_handle)
        return
    items = parse_items(html)
    for item in items:
        info = {'title': item['title'], 'year': item['year'], 'mediatype': 'movie'}
        ctx = [('[B]Exportar a Biblioteca[/B]', 'RunPlugin(' + build_url({'action': 'export_movie', 'url': item['url'], 'title': item['title']}) + ')')]
        add_item(item['title'], build_url({'action': 'play', 'url': item['url']}), poster=item['poster'], info=info, is_folder=False, is_playable=True, context_menu=ctx)
    if re.search(r'Siguiente|Next', html, re.I):
        add_item('>> Siguiente Pagina (' + str(page + 1) + ')', build_url({'action': 'peliculas', 'page': page + 1, 'genero': genero}))
    xbmcplugin.endOfDirectory(addon_handle)


# ===================== PELICULAS DESTACADAS =====================
def show_peliculas_destacadas():
    html = fetch(BASE_URL + '/peliculas?orden=tendencias')
    if not html:
        add_item('Error al cargar', '')
        xbmcplugin.endOfDirectory(addon_handle)
        return
    items = parse_items(html)
    for item in items:
        info = {'title': item['title'], 'year': item['year'], 'mediatype': 'movie'}
        ctx = [('[B]Exportar a Biblioteca[/B]', 'RunPlugin(' + build_url({'action': 'export_movie', 'url': item['url'], 'title': item['title']}) + ')')]
        add_item(item['title'], build_url({'action': 'play', 'url': item['url']}), poster=item['poster'], info=info, is_folder=False, is_playable=True, context_menu=ctx)
    xbmcplugin.endOfDirectory(addon_handle)


# ===================== SERIES =====================
def show_series(page=1, genero=''):
    url = BASE_URL + '/series'
    params = []
    if genero:
        params.append('genero=' + urllib.parse.quote(genero))
    if page > 1:
        params.append('page=' + str(page))
    if params:
        url += '?' + '&'.join(params)
    html = fetch(url)
    if not html:
        add_item('Error al cargar', '')
        xbmcplugin.endOfDirectory(addon_handle)
        return
    items = parse_items(html)
    for item in items:
        info = {'title': item['title'], 'year': item['year'], 'mediatype': 'tvshow'}
        add_item(item['title'], build_url({'action': 'serie_detalle', 'url': item['url']}), poster=item['poster'], info=info)
    if re.search(r'Siguiente|Next', html, re.I):
        add_item('>> Siguiente Pagina (' + str(page + 1) + ')', build_url({'action': 'series', 'page': page + 1, 'genero': genero}))
    xbmcplugin.endOfDirectory(addon_handle)


# ===================== SERIES DESTACADAS =====================
def show_series_destacadas():
    html = fetch(BASE_URL + '/series?orden=tendencias')
    if not html:
        add_item('Error al cargar', '')
        xbmcplugin.endOfDirectory(addon_handle)
        return
    items = parse_items(html)
    for item in items:
        info = {'title': item['title'], 'year': item['year'], 'mediatype': 'tvshow'}
        add_item(item['title'], build_url({'action': 'serie_detalle', 'url': item['url']}), poster=item['poster'], info=info)
    xbmcplugin.endOfDirectory(addon_handle)


# ===================== DETALLE SERIE (Netflix-style) =====================
def show_serie_detalle(series_url):
    html = fetch(series_url)
    if not html:
        add_item('Error al cargar', '')
        xbmcplugin.endOfDirectory(addon_handle)
        return
    title_m = re.search(r'<h1[^>]*>([^<]+)', html)
    series_title = dec(title_m.group(1).strip()) if title_m else ''
    poster_m = re.search(r'<img[^>]*src="(https://image\.tmdb\.org[^"]+)"', html)
    poster = poster_m.group(1).replace('/w1280/', '/w500/') if poster_m else ''

    # Find seasons and episodes in one pass
    season_links = re.findall(r'href="(https://cuevana3i\.you/serie/[^"]+/temporada-\d+)"', html)
    ep_links = re.findall(r'href="(https://cuevana3i\.you/serie/[^"]+/episodio-(\d+)x(\d+))"', html)

    seen_seasons = set()
    ctx = [('[B]Exportar Serie a Biblioteca[/B]', 'RunPlugin(' + build_url({'action': 'export_serie', 'url': series_url, 'title': series_title}) + ')')]
    for s_url in season_links:
        if s_url in seen_seasons:
            continue
        seen_seasons.add(s_url)
        s_num = re.search(r'temporada-(\d+)', s_url).group(1)
        info = {'title': series_title + ' - Temporada ' + s_num, 'mediatype': 'season', 'tvshowtitle': series_title}
        add_item('Temporada ' + s_num, build_url({'action': 'temporada', 'url': s_url, 'series': series_title}), poster=poster, info=info, context_menu=ctx)

    # If no season links, show episodes directly
    if not seen_seasons and ep_links:
        seen_eps = set()
        for ep_url, s, e in ep_links:
            if ep_url in seen_eps:
                continue
            seen_eps.add(ep_url)
            label = 'T%02dE%02d' % (int(s), int(e))
            info = {'title': label, 'season': int(s), 'episode': int(e), 'mediatype': 'episode', 'tvshowtitle': series_title}
            add_item(label, build_url({'action': 'servidores', 'url': ep_url}), poster=poster, info=info)

    xbmcplugin.endOfDirectory(addon_handle)


# ===================== TEMPORADA (Netflix-style) =====================
def show_temporada(season_url, series_name=''):
    html = fetch(season_url)
    if not html:
        add_item('Error al cargar', '')
        xbmcplugin.endOfDirectory(addon_handle)
        return
    poster_m = re.search(r'<img[^>]*src="(https://image\.tmdb\.org[^"]+)"', html)
    poster = poster_m.group(1).replace('/w1280/', '/w500/') if poster_m else ''

    series_slug_m = re.search(r'/serie/([^/]+)/temporada-', season_url)
    season_num_m = re.search(r'temporada-(\d+)', season_url)
    series_slug = series_slug_m.group(1) if series_slug_m else ''
    season_num = season_num_m.group(1) if season_num_m else ''

    ep_links = re.findall(r'href="(https://cuevana3i\.you/serie/[^"]+/episodio-(\d+)x(\d+))"', html)

    # Collect all episode URLs in order for auto-play
    all_ep_urls = []
    seen = set()
    for ep_url, s, e in ep_links:
        if ep_url in seen:
            continue
        seen.add(ep_url)
        all_ep_urls.append(ep_url)

    # Store episode list in a temp file for the player to read
    queue_file = os.path.join(addon.getAddonInfo('path'), 'episode_queue.txt')
    try:
        with open(queue_file, 'w') as f:
            for ep in all_ep_urls:
                f.write(ep + '\n')
    except Exception:
        pass

    seen2 = set()
    for ep_url, s, e in ep_links:
        if ep_url in seen2:
            continue
        seen2.add(ep_url)
        s_i, e_i = int(s), int(e)
        label = 'T%02dE%02d' % (s_i, e_i)
        if series_name:
            label = series_name + ' - ' + label

        info = {
            'title': label, 'season': s_i, 'episode': e_i,
            'mediatype': 'episode', 'tvshowtitle': series_name
        }
        play_url = build_url({'action': 'play', 'url': ep_url})
        add_item(label, play_url, poster=poster, info=info, is_folder=False, is_playable=True)

    xbmcplugin.endOfDirectory(addon_handle)


# ===================== EXPORTAR A BIBLIOTECA =====================

LIBRARY_PATH = os.path.join(xbmcvfs.translatePath(addon.getAddonInfo('profile')), 'library')


def export_serie_to_library(series_url, series_name):
    """Export a series to Kodi library via .strm files."""
    if not os.path.exists(LIBRARY_PATH):
        try:
            os.makedirs(LIBRARY_PATH)
        except Exception as e:
            xbmc.log('[Moob] Could not create library path: ' + str(e), xbmc.LOGERROR)
            return

    html = fetch(series_url)
    if not html:
        return

    poster_m = re.search(r'<img[^>]*src="(https://image\.tmdb\.org[^"]+)"', html)
    poster = poster_m.group(1).replace('/w1280/', '/w500/') if poster_m else ''

    # Create series folder
    series_slug = series_url.rstrip('/').split('/')[-1]
    series_folder = os.path.join(LIBRARY_PATH, series_name.replace(':', '').replace("'", ''))
    if not os.path.exists(series_folder):
        os.makedirs(series_folder)

    # Save poster
    if poster:
        try:
            poster_data = urllib.request.urlopen(poster).read()
            with open(os.path.join(series_folder, 'poster.jpg'), 'wb') as f:
                f.write(poster_data)
        except Exception:
            pass

    # Find all seasons
    season_links = re.findall(r'href="(https://cuevana3i\.you/serie/[^"]+/temporada-(\d+))"', html)
    seen_seasons = set()
    for season_url, s_num in season_links:
        if season_url in seen_seasons:
            continue
        seen_seasons.add(season_url)

        s_html = fetch(season_url)
        if not s_html:
            continue

        ep_links = re.findall(r'href="(https://cuevana3i\.you/serie/[^"]+/episodio-(\d+)x(\d+))"', s_html)
        seen_eps = set()
        for ep_url, s, e in ep_links:
            if ep_url in seen_eps:
                continue
            seen_eps.add(ep_url)
            s_i, e_i = int(s), int(e)

            # Create .strm file
            ep_title = 'S%02dE%02d' % (s_i, e_i)
            strm_path = os.path.join(series_folder, ep_title + '.strm')
            plugin_url = 'plugin://plugin.video.cuevana3/?action=play&url=' + urllib.parse.quote(ep_url)
            with open(strm_path, 'w') as f:
                f.write(plugin_url)

            # Create .nfo with metadata
            nfo_path = os.path.join(series_folder, ep_title + '.nfo')
            nfo_content = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<episodedetails>
  <title>{title}</title>
  <season>{season}</season>
  <episode>{episode}</episode>
  <showtitle>{showtitle}</showtitle>
</episodedetails>'''.format(title=ep_title, season=s_i, episode=e_i, showtitle=series_name)
            with open(nfo_path, 'w') as f:
                f.write(nfo_content)

    # Create tvshow.nfo
    nfo_path = os.path.join(series_folder, 'tvshow.nfo')
    nfo_content = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<tvshow>
  <title>{title}</title>
</tvshow>'''.format(title=series_name)
    with open(nfo_path, 'w') as f:
        f.write(nfo_content)

    xbmcgui.Dialog().notification('Moob', series_name + ' exportada a la biblioteca', xbmcgui.NOTIFICATION_INFO)


def export_movie_to_library(movie_url, movie_title):
    """Export a movie to Kodi library via .strm file."""
    if not os.path.exists(LIBRARY_PATH):
        os.makedirs(LIBRARY_PATH)

    movies_folder = os.path.join(LIBRARY_PATH, '_Peliculas')
    if not os.path.exists(movies_folder):
        os.makedirs(movies_folder)

    safe_title = movie_title.replace(':', '').replace("'", '').replace('/', '-')
    strm_path = os.path.join(movies_folder, safe_title + '.strm')
    plugin_url = 'plugin://plugin.video.cuevana3/?action=play&url=' + urllib.parse.quote(movie_url)
    with open(strm_path, 'w') as f:
        f.write(plugin_url)

    xbmcgui.Dialog().notification('Moob', movie_title + ' exportada a la biblioteca', xbmcgui.NOTIFICATION_INFO)


# ===================== AUTO-PLAY PLAYER =====================
class AutoPlayPlayer(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)
        self.episode_queue = []  # List of (ep_url, label) tuples
        self.current_idx = 0

    def onPlayBackEnded(self):
        self.current_idx += 1
        if self.current_idx < len(self.episode_queue):
            next_ep = self.episode_queue[self.current_idx]
            xbmc.log('[Moob] Auto-playing next: ' + next_ep[1], xbmc.LOGINFO)
            self._play_episode(next_ep[0])
        else:
            xbmc.log('[Moob] No more episodes to play', xbmc.LOGINFO)

    def _play_episode(self, ep_url):
        html = fetch(ep_url)
        if not html:
            return
        best = find_best_server(html)
        if not best:
            return
        embed_url = decode_server_url(best)
        video_url = resolve_video_url(embed_url)
        if video_url:
            play_item = xbmcgui.ListItem(path=video_url)
            if '.m3u8' in video_url:
                play_item.setProperty('inputstream', 'inputstream.adaptive')
                play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
                play_item.setProperty('inputstream.adaptive.stream_headers',
                    'User-Agent=' + urllib.parse.quote(HEADERS['User-Agent']) +
                    '&Referer=' + urllib.parse.quote(embed_url.split('/embed')[0] + '/'))
            self.play(video_url, play_item)


# ===================== RESOLVER SERVIDOR MEJOR =====================
def find_best_server(html):
    """Find the best server URL from the page. Priority: Hyper Latino > Hyper Castellano > Hyper Sub > Nebula > others."""
    # Parse language tabs
    tabs = re.findall(r'<li class="tab-video-item">(.*?)</li>', html, re.DOTALL)

    hyper_latino = []
    hyper_castellano = []
    hyper_sub = []
    nebula_servers = []
    other_servers = []

    for tab in tabs:
        lang_m = re.search(r'<div class="tab-item-name">\s*([^<]+)', tab)
        lang = dec(lang_m.group(1).strip()).lower() if lang_m else ''

        servers = re.findall(r'data-server="([^"]+)"[^>]*><span>\s*([^<]+)\s*</span>', tab)
        for s_url, s_name in servers:
            name = dec(s_name.strip()).lower()
            is_hyper = 'hyper' in name
            is_nebula = 'nebula' in name
            is_token = 'token=' in s_url

            if is_hyper and is_token:
                if 'latino' in lang or 'castellano' not in lang and 'subtitul' not in lang:
                    hyper_latino.append(s_url)
                elif 'castellano' in lang:
                    hyper_castellano.append(s_url)
                elif 'subtitul' in lang or 'multi' in lang:
                    hyper_sub.append(s_url)
                else:
                    hyper_latino.append(s_url)  # Default to latino if unclear
            elif is_nebula and is_token:
                nebula_servers.append(s_url)
            elif is_token or 'v=' in s_url:
                other_servers.append(s_url)

    # Return best available
    for pool in [hyper_latino, hyper_castellano, hyper_sub, nebula_servers, other_servers]:
        if pool:
            return pool[0]
    return None


# ===================== AUTO-SELECT PLAY =====================
def auto_select_and_play(content_url, next_url=''):
    """Auto-select best server and play directly without showing server list."""
    html = fetch(content_url)
    if not html:
        xbmcgui.Dialog().notification('Moob', 'Error al cargar contenido', xbmcgui.NOTIFICATION_ERROR)
        return

    best = find_best_server(html)
    if best:
        xbmc.log('[Moob] Auto-selected server: ' + best[:80], xbmc.LOGINFO)
        embed_url = decode_server_url(best)
        video_url = resolve_video_url(embed_url)
        if video_url:
            play_item = xbmcgui.ListItem(path=video_url)
            if '.m3u8' in video_url:
                play_item.setProperty('inputstream', 'inputstream.adaptive')
                play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
                play_item.setProperty('inputstream.adaptive.stream_headers',
                    'User-Agent=' + urllib.parse.quote(HEADERS['User-Agent']) +
                    '&Referer=' + urllib.parse.quote(embed_url.split('/embed')[0] + '/'))
            if next_url:
                player = AutoPlayPlayer()
                player.next_url = next_url
            xbmcplugin.setResolvedUrl(addon_handle, True, play_item)
        else:
            xbmcgui.Dialog().notification('Moob', 'No se pudo resolver. Intenta otro contenido.', xbmcgui.NOTIFICATION_ERROR)
    else:
        # Fallback: show server list
        show_servidores(content_url)


# ===================== SERVIDORES =====================
def show_servidores(content_url, series_url='', season='', episode=''):
    html = fetch(content_url)
    if not html:
        add_item('Error al cargar servidores', '')
        xbmcplugin.endOfDirectory(addon_handle)
        return
    poster_m = re.search(r'<img[^>]*src="(https://image\.tmdb\.org[^"]+)"', html)
    poster = poster_m.group(1).replace('/w1280/', '/w500/') if poster_m else ''

    # Build next episode URL if we have context
    next_url = ''
    if series_url and season and episode:
        next_ep = int(episode) + 1
        next_url = build_url({'action': 'servidores_next', 'series': series_url, 'season': season, 'episode': str(next_ep)})

    # Parse language tabs
    tabs = re.findall(r'<li class="tab-video-item">(.*?)</li>', html, re.DOTALL)
    for tab in tabs:
        lang_m = re.search(r'<div class="tab-item-name">\s*([^<]+)', tab)
        lang = dec(lang_m.group(1).strip()) if lang_m else ''
        servers = re.findall(r'data-server="([^"]+)"[^>]*><span>\s*([^<]+)\s*</span>', tab)
        for s_url, s_name in servers:
            name = dec(s_name.strip())
            label = '[' + lang + '] ' + name if lang else name
            resolve_url = build_url({'action': 'reproducir', 'url': s_url, 'next': next_url})
            li = xbmcgui.ListItem(label)
            li.setProperty('IsPlayable', 'true')
            if poster:
                li.setArt({'poster': poster, 'thumb': poster})
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=resolve_url, listitem=li, isFolder=False)

    if not tabs:
        servers = re.findall(r'data-server="([^"]+)"[^>]*>.*?<span[^>]*>([^<]+)</span>', html, re.DOTALL)
        for s_url, s_name in servers:
            name = dec(s_name.strip())
            resolve_url = build_url({'action': 'reproducir', 'url': s_url, 'next': next_url})
            li = xbmcgui.ListItem(name)
            li.setProperty('IsPlayable', 'true')
            if poster:
                li.setArt({'poster': poster, 'thumb': poster})
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=resolve_url, listitem=li, isFolder=False)

    xbmcplugin.endOfDirectory(addon_handle)


def show_servidores_next(series_url, season, episode):
    """Find the next episode's server page and play it automatically."""
    # Construct the next episode URL
    series_slug = series_url.rstrip('/').split('/')[-1]
    next_ep_url = BASE_URL + '/serie/' + series_slug + '/episodio-' + season + 'x' + episode
    xbmc.log('[Moob] Next episode URL: ' + next_ep_url, xbmc.LOGINFO)

    html = fetch(next_ep_url)
    if not html:
        xbmc.log('[Moob] Could not load next episode', xbmc.LOGERROR)
        return

    # Find first working server (prefer Hyper)
    servers = re.findall(r'data-server="([^"]+)"', html)
    for s_url in servers:
        if 'tungtungsahur' in s_url and 'token=' in s_url:
            # Check if it's Hyper (token starts with 1)
            token_m = re.search(r'token=([A-Za-z0-9]+)', s_url)
            if token_m and token_m.group(1)[0] == '1':
                xbmc.log('[Moob] Auto-playing Hyper server', xbmc.LOGINFO)
                embed_url = decode_server_url(s_url)
                video_url = resolve_video_url(embed_url)
                if video_url:
                    play_item = xbmcgui.ListItem(path=video_url)
                    if '.m3u8' in video_url:
                        play_item.setProperty('inputstream', 'inputstream.adaptive')
                        play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
                        play_item.setProperty('inputstream.adaptive.stream_headers',
                            'User-Agent=' + urllib.parse.quote(HEADERS['User-Agent']) +
                            '&Referer=' + urllib.parse.quote(embed_url.split('/embed')[0] + '/'))
                    # Set up next episode in chain
                    next_next = build_url({'action': 'servidores_next', 'series': series_url, 'season': season, 'episode': str(int(episode) + 1)})
                    player = AutoPlayPlayer()
                    player.next_url = next_next
                    player.next_label = 'T' + season + 'E' + str(int(episode) + 1)
                    xbmc.Player().play(video_url, play_item)
                    return

    # Fallback: try any token server
    for s_url in servers:
        if 'tungtungsahur' in s_url and 'token=' in s_url:
            embed_url = decode_server_url(s_url)
            video_url = resolve_video_url(embed_url)
            if video_url:
                play_item = xbmcgui.ListItem(path=video_url)
                if '.m3u8' in video_url:
                    play_item.setProperty('inputstream', 'inputstream.adaptive')
                    play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
                    play_item.setProperty('inputstream.adaptive.stream_headers',
                        'User-Agent=' + urllib.parse.quote(HEADERS['User-Agent']) +
                        '&Referer=' + urllib.parse.quote(embed_url.split('/embed')[0] + '/'))
                xbmc.Player().play(video_url, play_item)
                return

    xbmc.log('[Moob] No working server found for next episode', xbmc.LOGWARNING)


# ===================== REPRODUCIR =====================
def reproducir(server_url):
    xbmc.log('[Moob] Resolving: ' + server_url, xbmc.LOGINFO)
    embed_url = decode_server_url(server_url)
    xbmc.log('[Moob] Embed: ' + embed_url, xbmc.LOGINFO)
    video_url = resolve_video_url(embed_url)
    xbmc.log('[Moob] Video: ' + str(video_url), xbmc.LOGINFO)
    if video_url:
        play_item = xbmcgui.ListItem(path=video_url)
        if '.m3u8' in video_url:
            play_item.setProperty('inputstream', 'inputstream.adaptive')
            play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
            play_item.setProperty('inputstream.adaptive.stream_headers',
                'User-Agent=' + urllib.parse.quote(HEADERS['User-Agent']) +
                '&Referer=' + urllib.parse.quote(embed_url.split('/embed')[0] + '/'))
        xbmcplugin.setResolvedUrl(addon_handle, True, play_item)
    else:
        xbmcgui.Dialog().notification('Moob', 'No se pudo resolver. Intenta otro servidor.', xbmcgui.NOTIFICATION_ERROR)


# ===================== BUSQUEDA =====================
def busqueda():
    keyboard = xbmc.Keyboard('', 'Buscar peliculas y series...')
    keyboard.doModal()
    if keyboard.isConfirmed():
        query = keyboard.getText()
        if query:
            url = BASE_URL + '/explorar?s=' + urllib.parse.quote(query)
            html = fetch(url)
            if not html:
                add_item('Error al buscar', '')
                xbmcplugin.endOfDirectory(addon_handle)
                return
            items = parse_items(html)
            for item in items:
                prefix = '[MOVIE] ' if item['type'] == 'movie' else '[SERIE] '
                info = {'title': item['title'], 'year': item['year'], 'mediatype': item['type']}
                if item['type'] == 'movie':
                    add_item(prefix + item['title'], build_url({'action': 'play', 'url': item['url']}), poster=item['poster'], info=info, is_folder=False, is_playable=True)
                else:
                    add_item(prefix + item['title'], build_url({'action': 'serie_detalle', 'url': item['url']}), poster=item['poster'], info=info)
            if not items:
                add_item('No se encontraron resultados', '')
    xbmcplugin.endOfDirectory(addon_handle)


# ===================== ROUTER =====================
action = args.get('action', [None])[0]

if action is None:
    menu_principal()
elif action == 'peliculas':
    show_peliculas(int(args.get('page', [1])[0]), args.get('genero', [''])[0])
elif action == 'peliculas_destacadas':
    show_peliculas_destacadas()
elif action == 'series':
    show_series(int(args.get('page', [1])[0]), args.get('genero', [''])[0])
elif action == 'series_destacadas':
    show_series_destacadas()
elif action == 'generos_peliculas':
    show_generos_peliculas()
elif action == 'generos_series':
    show_generos_series()
elif action == 'serie_detalle':
    show_serie_detalle(args['url'][0])
elif action == 'temporada':
    show_temporada(args['url'][0], args.get('series', [''])[0])
elif action == 'servidores':
    show_servidores(args['url'][0], args.get('series', [''])[0], args.get('season', [''])[0], args.get('episode', [''])[0])
elif action == 'servidores_next':
    show_servidores_next(args['series'][0], args['season'][0], args['episode'][0])
elif action == 'reproducir':
    reproducir(args['url'][0])
elif action == 'play':
    # Auto-select and play directly
    next_url = args.get('next', [''])[0]
    auto_select_and_play(args['url'][0], next_url)
elif action == 'busqueda':
    busqueda()
elif action == 'export_serie':
    export_serie_to_library(args['url'][0], args['title'][0])
elif action == 'export_movie':
    export_movie_to_library(args['url'][0], args['title'][0])
