from flask import (Flask, request, abort, jsonify, redirect, render_template)
from flask_celery import make_celery
from post import Post
import arrow
import tweepy
from dotenv import load_dotenv
load_dotenv()
import os

# personal information
consumer_key = os.getenv("CONSUMER_KEY")
consumer_secret = os.getenv("CONSUMER_SECRET")
access_token = os.getenv("ACCESS_TOKEN")
access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)

twitter = tweepy.API(auth)

app = Flask(__name__)
app.config['CELERY_BROKER_URL'] = 'amqp://localhost//'
# app.config['CELERY_BACKEND'] = ''

celery = make_celery(app)

@app.route("/")
def index():
    return render_template('index.html')

@app.route('/', methods=['POST'])
def process():

    input = request.form.to_dict(flat=False)

    post = Post(
                name=input['text'],
                time=input['time'][0],
                # timezone=input['timezone'][0]
                timezone='US/Pacific'
            )
    # print('Original: ', post.time)
    post.time = arrow.get(post.time).replace(tzinfo=post.timezone)
    print('Created: ', post.time)
    print(post.time.humanize())
    # post.time = arrow.get(post.time, post.timezone).to('utc').naive
    post.time = arrow.get(post.time).to('utc').naive

    tweet.apply_async(args=post.name, eta=post.time)
    # tweet.apply_async((post.name), countdown=1)

    return 'I sent an async request yeet'

@app.route('/')
def default():
    return 'Yo dawg'

@celery.task(name='schedule.tweet')
def tweet(string):
    twitter.update_status(status=string)
    # print(twitter.home_timeline())
    return string

if __name__ == '__main__':
    app.run(host='0.0.0.0')
