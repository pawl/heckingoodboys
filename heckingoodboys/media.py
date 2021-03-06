import praw

from heckingoodboys import app, cache

MEDIA_CACHE_KEY = 'all_media'


class Media:
    """Image or video to be displayed on a slide."""
    title = None
    image_url = None
    video_url = None
    permalink = None

    def __init__(self, reddit_post):
        self.title = reddit_post.title
        self.permalink = reddit_post.permalink

        # determine the reddit post's image or video url, if it has one
        # TODO: support https://v.redd.it/i1058cwgfac31
        # TODO: support https://gfycat.com/welldocumentedunderstatedchevrotain
        url = reddit_post.url
        if ("imgur.com" in url) and url.endswith(".gifv"):
            # imgur gifv
            # just removing "v" from gifv doesn't work, need to use mp4 video
            self.video_url = url[:-4] + 'mp4'
        elif ("imgur.com" not in url) and url.endswith((".jpg", ".png", ".jpeg")):
            # non-imgur images (example: https://i.redd.it/f52s327v59c31.jpg)
            # only support images with previews
            if hasattr(reddit_post, "preview"):
                # get largest preview (source image is often too big)
                max_width = 0
                for resolution in reddit_post.preview['images'][0]['resolutions']:
                    width = resolution['width']
                    if max_width < width:
                        max_width = width
                        self.image_url = resolution['url']
        elif ("imgur.com" in url) and ("/a/" not in url):
            # imgur images (example: https://imgur.com/X5Jl2xd)
            if url.endswith("/new"):
                url = url.rsplit("/", 1)[0]
            imgur_post_id = url.rsplit("/", 1)[1].rsplit(".", 1)[0]
            # h = Huge Thumbnail (1024x1024)
            self.image_url = "http://i.imgur.com/" + imgur_post_id + "h.jpg"

    def __hash__(self):
        """Prevents 'TypeError: unhashable type' error when using Media in a set()."""
        return hash((self.title,))

    def __eq__(self, other):
        """Makes this class unique in a set()."""
        if not isinstance(other, type(self)):
            return False

        return self.title == other.title


def get_media():
    """Gets image and video urls from reddit."""
    app.logger.info('getting media from reddit...')

    reddit = praw.Reddit(
        client_id=app.config['REDDIT_CLIENT_ID'],
        client_secret=app.config['REDDIT_CLIENT_SECRET'],
        user_agent='praw')

    limit = 100 if app.debug else 1000
    reddit_posts = reddit \
        .multireddit('heckingoodboys', 'heckingoodboys') \
        .hot(limit=limit)

    all_media = set()
    for reddit_post in reddit_posts:
        media = Media(reddit_post)
        if media.video_url or media.image_url:
            all_media.add(media)

    app.logger.info('successfully got media from reddit')

    return all_media


def populate_cache_handler(event, context):
    """Handler to allow AWS lambda function to call function with args"""
    app.logger.info('populating cache...')
    cache.set(MEDIA_CACHE_KEY, get_media())
    app.logger.info('successfully populated cache')
    return {'message': 'success'}
