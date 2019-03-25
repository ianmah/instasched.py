from flask import (Flask, request, abort, jsonify, redirect, render_template)
from flask_celery import make_celery
import arrow
import uuid
import json
import codecs
import logging
from customimg import Img
from werkzeug.utils import secure_filename
# import tweepy
from dotenv import load_dotenv
load_dotenv()
import os
from instagram_private_api import (
    Client, ClientError, ClientLoginError,
    ClientCookieExpiredError, ClientLoginRequiredError,
    __version__ as client_version)

# personal information
# consumer_key = os.getenv("CONSUMER_KEY")
# consumer_secret = os.getenv("CONSUMER_SECRET")
# access_token = os.getenv("ACCESS_TOKEN")
# access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")
INSTA_USER = os.getenv("INSTA_USER")
INSTA_PW = os.getenv("INSTA_PW")
CREDENTIALS_JSON = "test_credentials.json"

# auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
# auth.set_access_token(access_token, access_token_secret)
#
# twitter = tweepy.API(auth)

app = Flask(__name__)
app.config['CELERY_BROKER_URL'] = 'amqp://localhost//'
# app.config['CELERY_BACKEND'] = ''

celery = make_celery(app)

def to_json(python_object):
    if isinstance(python_object, bytes):
        return {'__class__': 'bytes',
                '__value__': codecs.encode(python_object, 'base64').decode()}
    raise TypeError(repr(python_object) + ' is not JSON serializable')


def from_json(json_object):
    if '__class__' in json_object and json_object['__class__'] == 'bytes':
        return codecs.decode(json_object['__value__'].encode(), 'base64')
    return json_object


def onlogin_callback(api, new_settings_file):
    cache_settings = api.settings
    with open(new_settings_file, 'w') as outfile:
        json.dump(cache_settings, outfile, default=to_json)
        print('SAVED: {0!s}'.format(new_settings_file))


logging.basicConfig()
logger = logging.getLogger('instagram_private_api')
logger.setLevel(logging.WARNING)

print('Client version: {0!s}'.format(client_version))

device_id = None
try:

    settings_file = CREDENTIALS_JSON
    if not os.path.isfile(settings_file):
        # settings file does not exist
        print('Unable to find file: {0!s}'.format(settings_file))

        # login new
        instagram = Client(
            INSTA_USER, INSTA_PW,
            on_login=lambda x: onlogin_callback(x, CREDENTIALS_JSON))
    else:
        with open(settings_file) as file_data:
            cached_settings = json.load(file_data, object_hook=from_json)
        print('Reusing settings: {0!s}'.format(settings_file))

        device_id = cached_settings.get('device_id')
        # reuse auth settings
        instagram = Client(
            INSTA_USER, INSTA_PW,
            settings=cached_settings)

except (ClientCookieExpiredError, ClientLoginRequiredError) as e:
    print('ClientCookieExpiredError/ClientLoginRequiredError: {0!s}'.format(e))

    # Login expired
    # Do relogin but use default ua, keys and such
    instagram = Client(
        INSTA_USER, INSTA_PW,
        device_id=device_id,
        on_login=lambda x: onlogin_callback(x, CREDENTIALS_JSON))

except ClientLoginError as e:
    print('ClientLoginError {0!s}'.format(e))
    exit(9)
except ClientError as e:
    print('ClientError {0!s} (Code: {1:d}, Response: {2!s})'.format(e.msg, e.code, e.error_response))
    exit(9)
except Exception as e:
    print('Unexpected Exception: {0!s}'.format(e))
    exit(99)

# Show when login expires
# cookie_expiry = instagram.cookie_jar.auth_expires
# print('Cookie Expiry: {0!s}'.format(datetime.datetime.fromtimestamp(cookie_expiry).strftime('%Y-%m-%dT%H:%M:%SZ')))

UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = set(['jpg', 'jpeg', 'png'])

posts = {}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    return render_template('index.html')

@app.route('/', methods=['POST'])
def process():
    input = request.form.to_dict(flat=False)

    file = request.files['file']
    # if user does not select file, browser also
    # submit a empty part without filename
    if file.filename == '':
        print('No selected file')
        return redirect(request.url)
    if not allowed_file(file.filename):
        print('Invalid file type')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        input['filename'] = filename
        id = str(uuid.uuid4())
        input['id'] = id
        post = handleInput(input)

        createPost.apply_async([post], eta=post['time'])
        # print(posts)
        # createPost.delay(post)
    return 'Success'

def handleInput(input):
    post = {}
    post['name']=input['text']
    post['time']=input['time'][0]
    post['file']=input['filename']
    post['timezone']='US/Pacific'
    # json_data = json.dumps(post)

    post['time'] = arrow.get(post['time']).replace(tzinfo=post['timezone'])
    # print('Created:', post.time)
    print(post['time'].humanize())
    post['time'] = arrow.get(post['time']).to('utc').naive
    # createPost.apply_async(args=post, eta=post.time)

    posts[input['id']] = post
    return post

@celery.task(name='schedule.createPost')
def createPost(post):
    # id = idv[0]
    # post = posts[id]
    initImg = Img("./uploads/" + post['file'])
    initImg.getImg().show()
    size = initImg.size()
    # print(size)
    imgByteArr = initImg.getByteArr()
    instagram.post_photo(imgByteArr, size, caption=post['name'])
    # twitter.update_status(status=string)
    print('Posted image', post['name'])
    posts[id] = None

if __name__ == '__main__':
    app.run(host='0.0.0.0')
