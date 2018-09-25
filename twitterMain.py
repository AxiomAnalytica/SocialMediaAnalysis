from bs4 import BeautifulSoup # Used to parse HTML
from textblob import TextBlob # Used to get noun phrases and sentiment
import re
import operator
from wordcloud import WordCloud
import requests
import json
import base64

def getTimeOfDay(elem):
    #Finds the unix time for the given elem
    #Outputs the string representing the time
    small = elem.find("small", attrs={'class': 'time'})
    link = small.find('a')
    span = link.find('span', attrs={'class':'_timestamp js-short-timestamp '})
    unixTime = int(span.get('data-time')) #Unix time of posting. Use to find time of day
    unixTime -= 4*3600 #Adjust for timezone difference. 4 Hours behind. Makes it EST
    rawHours = (unixTime%86400)/3600
    hours = int(rawHours) #Gets into representing number of hours since midnight tweet was posted
    minutes = int((rawHours%1)*60) #minutes into day
    polarity= "am"
    if hours>=12:
        polarity="pm"
    if hours==0:
        hours=12
        polarity="am"
    if hours>12:
        hours-=12
    timeString = str(hours) + ":" + str(minutes) + " " + polarity
    return timeString

def encodeImage(image):
    f = open(image, "rb")
    imageContents = f.read()
    f.close()
    return base64.b64encode(imageContents)

def getLocalImageData(image):
    requestURL = r'https://vision.googleapis.com/v1/images:annotate?key=AIzaSyB1p9Snl1kFujEK2-TugWhRvs7tJxXw_Og'
    f = open("localImage.json","rb")
    contents = f.read()
    f.close()
    contents = contents.replace(b'IMAGE_DATA', encodeImage(image))
    data = json.loads(contents)
    r = requests.post(requestURL, json=data)
    return r.json()

def parseLabelsFromJson(json):
    #This function will parse the labels out of the json object returned by getLocalImageData
    labels = []
    for elem in json['responses'][0]['labelAnnotations']:
        labels.append(elem['description'])
    return labels

def getNumReplies(tweet):
    #Gets the number of replies for a given tweet
    replyStr = tweet.parent.parent.find("span", attrs={'id': re.compile('profile-tweet-action-reply-count')})
    replyStr = str(replyStr.text)
    replyStr = replyStr.replace(",", "")
    replyStr = replyStr.replace(" replies", "")
    return int(replyStr)

def getNumRetweets(tweet):
    #Gets the number of retweets for a given tweet
    retweetStr = tweet.parent.parent.find("span", attrs={'id': re.compile('profile-tweet-action-retweet-count')})
    retweetStr = str(retweetStr.text)
    retweetStr = retweetStr.replace(",", "")
    retweetStr = retweetStr.replace(" retweets", "")
    return int(retweetStr)

def getNumLikes(tweet):
    #Gets the number of likes for a given tweet
    likeStr = tweet.parent.parent.find("span", attrs={'id': re.compile('profile-tweet-action-favorite-count')})
    likeStr = str(likeStr.text)
    likeStr = likeStr.replace(",", "")
    likeStr = likeStr.replace(" likes", "")
    return int(likeStr)

def getData(file):
    # Returns a list of [parsed tweets, totalTweets, totalReplies, totalRetweets, totalLikes]
    # Basically gets all the data from the tweets in the given HTML

    f = open(file, encoding='utf-8')
    content = f.read()
    f.close()

    soup = BeautifulSoup(content, "lxml")

    tweets = []
    totalReplies = 0
    totalRetweets = 0
    totalLikes = 0
    divs = soup.find_all("div", attrs={'class': 'js-tweet-text-container'})
    for elem in divs:
        children = elem.findChildren()
        tweet = children[0]
        text = tweet.text
        blob = TextBlob(text)
        nounPhrases = blob.noun_phrases
        sentiment =  blob.sentiment

        imageTags = elem.findAll("img")
        labels = []

        replies = getNumReplies(tweet)

        retweets = getNumRetweets(tweet)

        likes = getNumLikes(tweet)

        timeString = getTimeOfDay(tweet.parent.parent)
        tweets.append([nounPhrases,sentiment,likes,replies,retweets,timeString,labels])
        totalLikes+=likes
        totalReplies+=replies
        totalRetweets+=retweets

    return [tweets,totalReplies,totalRetweets,totalLikes]

def getTextWordclouds(tweets, excludeList):
    #This function takes in the list of tweets
    #and generates and saves all the desired word clouds
    #from the data

    wordToLike = {} #Dict mapping word to likes frequencies
    wordToReplies = {} #Dict mapping word to reply frequencies
    wordToRetweets = {} #Dict mapping word to retweet frequencies

    for tweet in tweets:
        nouns = tweet[0]  # Array of all noun phrases
        likes = tweet[2]  # Number of likes for this post
        replies = tweet[3]  # Number of replies for this post
        retweets = tweet[4] # Number of retweets for this post

        for noun in nouns:
            if noun not in excludeList:
                if noun in wordToLike:
                    wordToLike[noun] += float(likes)
                if noun not in wordToLike:
                    wordToLike[noun] = float(likes)
                if noun in wordToReplies:
                    wordToReplies[noun] += float(replies)
                if noun not in wordToReplies:
                    wordToReplies[noun] = float(replies)
                if noun in wordToRetweets:
                    wordToRetweets[noun] += float(retweets)
                if noun not in wordToRetweets:
                    wordToRetweets[noun] = float(retweets)

    #Sort arrays and generate coressponding dictionaries
    nounsByLikesSorted = sorted(wordToLike.items(), key=operator.itemgetter(1), reverse=True)
    topNounsByLikes = dict(nounsByLikesSorted[:20])
    bottomNounsByLikes = dict(nounsByLikesSorted[-20:])
    nounsByRepliesSorted = sorted(wordToReplies.items(), key=operator.itemgetter(1), reverse=True)
    topNounsByReplies = dict(nounsByRepliesSorted[:20])
    bottomNounsByReplies = dict(nounsByRepliesSorted[-20:])
    nounsByRetweetsSorted = sorted(wordToRetweets.items(), key=operator.itemgetter(1), reverse=True)
    topNounsByRetweets = dict(nounsByRetweetsSorted[:20])
    bottomNounsByReweets = dict(nounsByRetweetsSorted[-20:])

    #Generate and Save wordclouds
    WordCloud(width=600,height=300).generate_from_frequencies(frequencies=topNounsByLikes).to_file("topNounsByLikesTextTwitter.png")
    WordCloud(width=600,height=300).generate_from_frequencies(frequencies=bottomNounsByLikes).to_file("bottomNounsByLikesTextTwitter.png")
    WordCloud(width=600,height=300).generate_from_frequencies(frequencies=topNounsByReplies).to_file("topNounsByRepliesTextTwitter.png")
    WordCloud(width=600,height=300).generate_from_frequencies(frequencies=bottomNounsByReplies).to_file("bottomNounsByRepliesTextTwitter.png")
    WordCloud(width=600,height=300).generate_from_frequencies(frequencies=topNounsByRetweets).to_file("topNounsByRetweetsTextTwitter.png")
    WordCloud(width=600,height=300).generate_from_frequencies(frequencies=bottomNounsByReweets).to_file("bottomNounsByReweetsTextTwitter.png")

def getLabelsWordclouds(tweets, excludeList):
    #This function takes the list of tweets and creates wordcloud
    #correlating labels of pictures to number of likes, retweets, and replies

    labelToLike = {}  # Dict mapping label to likes frequencies
    labelToReplies = {}  # Dict mapping word to reply frequencies
    labelToRetweets = {}  # Dict mapping word to retweet frequencies

    for tweet in tweets:
        likes = tweet[2]  # Number of likes for this post
        replies = tweet[3]  # Number of replies for this post
        retweets = tweet[4]  # Number of retweets for this post
        labels = tweet[5]

        for label in labels:
            #print(label)
            if label not in excludeList:
                if label in labelToLike:
                    labelToLike[label] += float(likes)
                if label not in labelToLike:
                    labelToLike[label] = float(likes)
                if label in labelToReplies:
                    labelToReplies[label] += float(replies)
                if label not in labelToReplies:
                    labelToReplies[label] = float(replies)
                if label in labelToRetweets:
                    labelToRetweets[label] += float(retweets)
                if label not in labelToRetweets:
                    labelToRetweets[label] = float(retweets)

    # Sort arrays and generate coressponding dictionaries
    labelsByLikesSorted = sorted(labelToLike.items(), key=operator.itemgetter(1), reverse=True)
    topLabelsByLikes = dict(labelsByLikesSorted[:20])
    bottomLabelsByLikes = dict(labelsByLikesSorted[-20:])
    labelsByRepliesSorted = sorted(labelToReplies.items(), key=operator.itemgetter(1), reverse=True)
    topLabelsByReplies = dict(labelsByRepliesSorted[:20])
    bottomLabelsByReplies = dict(labelsByRepliesSorted[-20:])
    labelsByRetweetsSorted = sorted(labelToRetweets.items(), key=operator.itemgetter(1), reverse=True)
    topLabelsByRetweets = dict(labelsByRetweetsSorted[:20])
    bottomLabelsByRetweets = dict(labelsByRetweetsSorted[-20:])

    # Generate and Save wordclouds
    WordCloud(width=600, height=300).generate_from_frequencies(frequencies=topLabelsByLikes).to_file("topLabelsByLikesMediaTwitter.png")
    WordCloud(width=600, height=300).generate_from_frequencies(frequencies=bottomLabelsByLikes).to_file("bottomLabelsByLikesMediaTwitter.png")
    WordCloud(width=600, height=300).generate_from_frequencies(frequencies=topLabelsByReplies).to_file("topLabelsByRepliesMediaTwitter.png")
    WordCloud(width=600, height=300).generate_from_frequencies(frequencies=bottomLabelsByReplies).to_file("bottomLabelsByRepliesMediaTwitter.png")
    WordCloud(width=600, height=300).generate_from_frequencies(frequencies=topLabelsByRetweets).to_file("topLabelsByRetweetsMediaTwitter.png")
    WordCloud(width=600, height=300).generate_from_frequencies(frequencies=bottomLabelsByRetweets).to_file("bottomLabelsByRetweetsMediaTwitter.png")

def createDateGraphRows(posts):
    # This function will take in the list of posts and return
    # the string of rows to use for the date chart
    likeStr = "\n"  # String for time -> likes
    commentStr = "\n"  # String for time -> comments
    timeListLikes = []  # Times I have likes listed for
    timeListComments = []  # Times I have comments listed for

    for post in posts:
        date = post[5]
        time = date.split(" ")  # Time before cleaning it into a format Charts understands
        am = (time[1].lower() == "am")
        splitTime = time[0].split(":")
        hour = int(splitTime[0], 10)
        if am == False:
            hour += 12
        minutes = splitTime[1]
        time = str(hour) + ":" + str(minutes)

        if time in timeListLikes:
            i = timeListLikes.index(time)
            timeListLikes[i][1] += post[2]
        else:
            timeListLikes.append([time, post[2]])

        if time in timeListComments:
            i = timeListComments.index(time)
            timeListComments[i][1] += post[3]
        else:
            timeListComments.append([time, post[3]])

	#Add filler data where there isn't any from post to make spikes
	#in activity clearer
    for hour in range(1, 25):
        for minutes in range(1, 61):
            time = str(hour) + ":" + str(minutes)
            if time not in timeListLikes:
                timeListLikes.append([time, 0])
            if time not in timeListComments:
                timeListComments.append([time, 0])

    for elem in timeListLikes:
        time = elem[0].split(":")
        hour = time[0]
        minutes = time[1]
        likeStr += "[new Date(2000,0, 1, " + str(hour) + ", " + minutes + ", 00), " + str(elem[1]) + "],\n"

    for elem in timeListComments:
        time = elem[0].split(":")
        hour = time[0]
        minutes = time[1]
        commentStr += "[new Date(2000,0, 1, " + str(hour) + ", " + minutes + ", 00), " + str(elem[1]) + "],\n"

    return likeStr, commentStr

def createReport(tweets,textExcludeList,imageExcludeList):
    #This function will be used to generate the report about the tweets
    f = open("reportTemplate.html")
    report = f.read()
    f.close()

    getTextWordclouds(tweets,textExcludeList) # Generates the word clouds from the text data and saves them to the appropriate file
    #getLabelsWordclouds(tweets,imageExcludeList) # Generates the word clouds from the image data and saves them to the appropriate file
    timeCommentStr, timeLikeStr = createDateGraphRows(tweets)

    report = report.replace("DATE_GRAPH_TWITTER_LIKES", timeLikeStr)
    report = report.replace("DATE_GRAPH_TWITTER_REPLIES", timeCommentStr)

    f = open("reportTest.html", "wb+")
    f.write(report.encode('utf-8'))
    f.close()

if __name__ == "__main__":
	#Chose Trump's twitter due to large amount of varied data posted consistently
    textExcludeList = [] #Words to exclude from text search
	imageExcludeList = [] #Words to exclude from labels from images
    tweets,totalReplies,totalRetweets,totalLikes = getData("trumpTwitter.html") 
    createReport(tweets,[],[])