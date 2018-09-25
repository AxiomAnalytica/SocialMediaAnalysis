from bs4 import BeautifulSoup
import requests
from textblob import TextBlob
from textblob.np_extractors import FastNPExtractor
import os
import base64
import json
import operator
from wordcloud import WordCloud


videoCounter = 0
photoCounter = 0
totalPosts = 0
totalLikes = 0
totalReplies = 0

def getSoup(url):
    #Gets the soup for the given URL
    page = requests.get(url).content
    return BeautifulSoup(page,'lxml')

def getNextPage(soup):
    #Finds the URL of the next page of posts
    #Returns the empty string if last page
    nextPageNav = soup.find('nav',{'class':'next-cont'})
    if nextPageNav != None:
        if len(nextPageNav.findChildren()) != 0:
            return nextPageNav.findChildren()[0]['href']
        else:
            return ""
    return ""
    
def getPosts(soup):
    #Gets all the posts on this page
    posts = soup.findAll("article",{'class':'item clearfix'})
    return posts
    
def getMedia(url,video):
    #Gets photo or video associated with post, saves it to a local file, 
    # and returns the filename of the media
    global photoCounter
    global videoCounter
    if video==True:
        page = requests.get(url).content
        soup = BeautifulSoup(page,'lxml')
        mediaURL = soup.find("article",{'class': 'post-item-detail'}).find("source")['src']
        if os.path.split(os.getcwd())[1] != 'media':
            newPath = os.path.join(os.getcwd(),'media')
            os.chdir(newPath)
        video = requests.get(mediaURL).content
        filename = str(videoCounter) + ".mp4"
        f = open(filename,"wb")
        f.write(video)
        f.close()
        videoCounter += 1
        return filename
    else:
        page = requests.get(url).content
        soup = BeautifulSoup(page,'lxml')
        mediaURL = soup.find("article",{'class': 'post-item-detail'}).find("img")['src']
        if os.path.split(os.getcwd())[1] != 'media':
            newPath = os.path.join(os.getcwd(),'media')
            os.chdir(newPath)
        photo = requests.get(mediaURL).content
        filename = str(photoCounter) + ".jpg"
        f = open(filename,"wb")
        f.write(photo)
        f.close()
        photoCounter += 1
        return filename
    
def getData(rawPosts):
    global totalPosts
    global totalLikes
    global totalReplies
    extractor = FastNPExtractor()
    tmp = []
    for elem in rawPosts:
        element = elem.findAll("p",{"class": "content"})
        if element != []:
            text = element[0].text
            blob = TextBlob(text, np_extractor=extractor)
            nouns = blob.noun_phrases #Nouns in Caption
            sentiment = blob.sentiment #Sentiment of Caption
            #mediaURL = elem.findAll("a")[0]['href'] #URL of individual post. Used to get URL of media
            numComments = int(elem.find("span",{'class': 'comments'}).text.strip(),10) #Gets Number of Comments
            timePosted = elem.find("span",{'class': 'time'}).text.strip() #Gets Time
            numLikes = int(elem.find("span",{'class': 'like'}).text.strip(),10) #Gets Number of Likes
            filename = ""
            #if elem.find("div",{'class': 'content-image image'}) != None:
                #filename = getMedia(mediaURL,False)
            #else:
                #filename = getMedia(mediaURL,True)
            tmp.append([nouns,sentiment,numLikes,numComments,timePosted,filename])
            totalPosts += 1
            totalReplies += numComments
            totalLikes += numLikes
    return tmp

def getWordclouds(posts, excludeList):
    #This function takes in the list of posts
    #and generates and saves all the desired word clouds
    #from the data

    wordToLike = {} #Dict mapping word to likes frequencies
    wordToReplies = {} #Dict mapping word to reply frequencies

    for post in posts:
        nouns = post[0]  # Array of all noun phrases
        likes = post[2]  # Number of likes for this post
        replies = post[3]  # Number of replies for this post

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

    #Sort arrays and generate coressponding dictionaries
    nounsByLikesSorted = sorted(wordToLike.items(), key=operator.itemgetter(1), reverse=True)
    topNounsByLikes = dict(nounsByLikesSorted[:20])
    bottomNounsByLikes = dict(nounsByLikesSorted[-20:])
    nounsByRepliesSorted = sorted(wordToReplies.items(), key=operator.itemgetter(1), reverse=True)
    topNounsByReplies = dict(nounsByRepliesSorted[:20])
    bottomNounsByReplies = dict(nounsByRepliesSorted[-20:])

    #Generate and Save wordclouds
    WordCloud(width=600,height=300).generate_from_frequencies(frequencies=topNounsByLikes).to_file("topLikesWordCloudInstagram.png")
    WordCloud(width=600,height=300).generate_from_frequencies(frequencies=bottomNounsByLikes).to_file("bottomNounsByLikesInstagram.png")
    WordCloud(width=600,height=300).generate_from_frequencies(frequencies=topNounsByReplies).to_file("topNounsByRepliesInstagram.png")
    WordCloud(width=600,height=300).generate_from_frequencies(frequencies=bottomNounsByReplies).to_file("bottomNounsByRepliesInstagram.png")
    
def encodeImage(image):
    os.chdir(r'C:\Users\dmoore\Documents\InstaScrape\media')
    f = open(image,"rb")
    imageContents=f.read()
    f.close()
    return base64.b64encode(imageContents)
    
def getLocalImageData(image):
    requestURL = r'https://vision.googleapis.com/v1/images:annotate?key=AIzaSyB1p9Snl1kFujEK2-TugWhRvs7tJxXw_Og'
    f = open("localImage.json", "rb")
    contents = f.read()
    f.close()
    contents = contents.replace(b"IMAGE_DATA",encodeImage(image))
    data = json.loads(contents)
    r = requests.post(requestURL,json=data)
    return r.json()

def parseLabelsFromJson(json):
    #This function will parse the labels out of the json object returned by getLocalImageData
    print(json['responses'])
    for elem in json['responses'][0]['labelAnnotations']:
        print(elem['description'])

def getRemoteImageData(url):
    requestURL = r'https://vision.googleapis.com/v1/images:annotate?key=AIzaSyB1p9Snl1kFujEK2-TugWhRvs7tJxXw_Og'
    f = open("webImage.json")
    contents = f.read()
    f.close()
    contents = contents.replace("IMAGE_URL",url)
    data = json.loads(contents)
    r = requests.post(requestURL,json=data)
    print(r.json())
  
def createDateGraphRows(posts):
    #This function will take in the list of posts and return
    #the string of rows to use for the date chart
    likeStr = "\n" #String for time -> likes
    commentStr = "\n" #String for time -> comments
    timeListLikes = [] #Times I have likes listed for
    timeListComments = [] #Times I have comments listed for
    
    for post in posts:
        date = post[4]
        time = date.split(" ")[0] #Time before cleaning it into a format Charts understands
        am = (time[-2:].lower() == "am")
        time = time[:-2]
        splitTime = time.split(":")
        hour = int(splitTime[0],10)
        hour-=5
        if hour<=0:
            hour = 12+hour
            am = not am
        if am==False:
            hour+=12
        minutes = splitTime[1]
        time = str(hour) + ":" + str(minutes)
        
        if time in timeListLikes:
            i = timeListLikes.index(time)
            timeListLikes[i][1] += post[2]
        else:
            timeListLikes.append([time,post[2]])
            
        if time in timeListComments:
            i = timeListComments.index(time)
            timeListComments[i][1] += post[3]
        else:
            timeListComments.append([time,post[3]])
    
	#Add filler data where there isn't any from post to make spikes
	#in activity clearer
    for hour in range(1,25):
        for minutes in range(1,61):
            time = str(hour) + ":" + str(minutes)
            if time not in timeListLikes:
                timeListLikes.append([time,0])
            if time not in timeListComments:
                timeListComments.append([time,0])
    
    for elem in timeListLikes:
        time = elem[0].split(":")
        hour = time[0]
        minutes=time[1]
        likeStr+= "[new Date(2000,0, 1, " + str(hour) +", " + minutes + ", 00), " + str(elem[1]) + "],\n"
        
    for elem in timeListComments:
        time = elem[0].split(":")
        hour = time[0]
        minutes=time[1]
        commentStr += "[new Date(2000,0, 1, " + str(hour) +", " + minutes + ", 00), " + str(elem[1]) + "],\n"
    
    return likeStr,commentStr
  
def createReport(posts,excludeList):
    #This method generates the report
    f = open("reportTemplate.html")
    report = f.read()
    f.close()
    
    timeCommentStr, timeLikeStr = createDateGraphRows(posts)
    getWordclouds(posts, excludeList)  # Generates the word clouds from the posts and saves them to the appropriate file

    report = report.replace("DATE_GRAPH_INSTAGRAM_LIKES",timeLikeStr)
    report = report.replace("DATE_GRAPH_INSTAGRAM_COMMENTS",timeCommentStr)
    report = report.replace("TOTAL_INSTAGRAM_POSTS",str(totalPosts))

    f = open("reportTest.html","wb+")
    f.write(report.encode('utf-8'))
    f.close()
    
if __name__ == "__main__":

	excludeList = []
    posts = []
    soup = getSoup(URL)
    rawPosts = getPosts(soup)
    posts += getData(rawPosts)
    nextURL = getNextPage(soup)
    while nextURL != "":
        soup = getSoup(nextURL)
        rawPosts = getPosts(soup)
        posts += getData(rawPosts)
        nextURL = getNextPage(soup)
    createReport(posts,excludeList)