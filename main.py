import sqlite3
from PIL import Image, ImageDraw, ImageFilter
import os
import shutil
import glob
import mimetypes
mimetypes.init()
import requests
import json

path = os.path.dirname(os.path.abspath(__file__)) + "/storage" # Base path
session = requests.Session() # Session for requests

def initialize(): # Initializes basic stuff
    if not os.path.exists(path):
        os.mkdir(path)
    
    initializeTables = False
    if not os.path.exists(path + "/data.db"):
        initializeTables = True

    connection = sqlite3.connect(path + "/data.db")
    dbCursor = connection.cursor()

    dbCursor.execute("PRAGMA foreign_keys = ON") # Enabling foreign key constraints

    if initializeTables:
        makeTables(dbCursor) # If tables are not created, create them
    return connection, dbCursor

def makeTables(dbCursor): # Creates tables
    dbCursor.execute("""CREATE TABLE Profile(pk PRIMARY KEY, username, full_name,
                     page_name, biography, is_private, public_email, media_count,
                     follower_count, following_count, past_profiles, is_profile_downloaded)""")
    
    dbCursor.execute("""CREATE TABLE Post(pk, link, number_of_items, caption, timestamp, isTag,
                     PRIMARY KEY(pk, link), FOREIGN KEY(pk) REFERENCES Profile(pk))""")

    dbCursor.execute("""CREATE TABLE Highlight(highlight_id, pk, title, PRIMARY KEY(highlight_id),
                     FOREIGN KEY(pk) REFERENCES Profile(pk))""")
    
    dbCursor.execute("""CREATE TABLE Story(pk, story_pk, highlight_id, timestamp, PRIMARY KEY(pk, story_pk, highlight_id),
                     FOREIGN KEY(pk) REFERENCES Profile(pk), FOREIGN KEY(highlight_id) REFERENCES Highlight(highlight_id))""")

def makeThumbnail(address): # Makes a thumbnail for given image and saves it
    try:
        image = Image.open(path + address)
        resized_image = image.resize((128, 128)) # Thumbnail size

        blur_radius = 2 # Radius of blurring the edges of the circle thumbnail
        offset = blur_radius * 2
        mask = Image.new("L", resized_image.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((offset, offset, resized_image.size[0] - offset, resized_image.size[1] - offset), fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(blur_radius))

        resized_image.putalpha(mask) # Making the edges transparent

        resized_image.save(path + address[:address.rindex('.')] + "_thumbnail.png") # Saving thumbnail at the same path
        
        return True
    
    except:
        return False # Couldn't make the thumbnail

def guessType(file): # Guesses the type of the file
    mimestart = mimetypes.guess_type(path + file)[0] # Guessing the type of the file

    if mimestart != None:
        mimestart = mimestart.split('/')[0]

        if mimestart == 'image':
            return 'Photo'
        elif mimestart == 'video':
            return 'Video'
        
    return 'None' # Couldn't guess or it wasn't image or video

def downloadLink(link, address): # Downloads the link and saves it to the address
    # Needs change for GUI implementation and multithreading
    try:
        media = requests.get(link, allow_redirects=True)
        open(path + address, 'wb').write(media.content) # saving the file
        return True
    
    except:
        return False # Couldn't download the link

def tryDownloading(link, address): # Tries to download the link for 5 times
    isDownloaded = downloadLink(link, address)
    if not isDownloaded: # If couldn't download the link, Try 5 more times
        for i in range(5):
            isDownloaded = downloadLink(link, address)
            if isDownloaded:
                return True

        if not isDownloaded:
            return False # Couldn't download the link
        
    return True

def listProfiles(): # Lists the profiles
    # Needs change for GUI implementation
    if os.name == 'nt': # Clearing the screen
        os.system('cls')

    else:
        os.system('clear')
    
    for profile in profiles:
        print(profile[1] + ":\n" + profile[2] + "\n" + profile[3] + "\nPosts: " + str(profile[5])
              + "\nFollowers: " + str(profile[6]) + "\nFollowings: " + str(profile[7])) # Show the details of each profile
        print("---------------------------------")

def addProfile(username): # Adds a profile
    try:
        for profile in profiles:
            if profile[1] == username:
                print("This account is already added!")
                return # profile already exist, don't need to continue
        
        response = session.get(f'https://anonyig.com/api/ig/userInfoByUsername/{username}')
        if response.status_code != 200:
            print("There was an error!")
            return # couldn't get the data
        
        data = json.loads(response.text)
        data = data['result']['user']
        
        if not os.path.exists(path + f"/{username}"): # Make the folders for the profile
            os.mkdir(path + f"/{username}")
        
        if not os.path.exists(path + f"/{username}/Profiles"):
            os.mkdir(path + f"/{username}/Profiles")
        
        pk = int(data["pk"])
        username = data["username"]
        full_name = data["full_name"]
        page_name = data["page_name"]
        biography = data["biography"]
        is_private = data["is_private"]
        if is_private:
            is_private = 1
        else:
            is_private = 0
        if "public_email" in data.keys():
            public_email = data["public_email"]
        else:
            public_email = None
        media_count = data["media_count"]
        follower_count = data["follower_count"]
        following_count = data["following_count"]

        original_profile_pic_link = data["hd_profile_pic_url_info"]["url"]
        format = original_profile_pic_link[:original_profile_pic_link.index("?")]
        format = format[format.rindex("."):]
        original_profile_pic = f"/{username}/Profiles/Profile{format}"

        past_profiles = 0
        is_profile_downloaded = 0

        isDownloaded = tryDownloading(original_profile_pic_link, original_profile_pic) # Try downloading the profile picture
        if not isDownloaded:
            print("There was an error!")
            return

        if not makeThumbnail(original_profile_pic): # Try Making a thumbnail for the profile picture
            print("There was an error!")
            return

        instruction = f"""INSERT INTO Profile VALUES({pk}, "{username}", "{full_name}","""

        if page_name is None:
            instruction += "NULL"
        else:
            instruction += f"""'{page_name}'"""
        
        if biography == '':
            instruction += f", NULL"
        else:
            instruction += f""", '{biography}'"""

        instruction += f""", {is_private},"""

        if (public_email is None) or (public_email == ''):
            instruction += "NULL"
        else:
            instruction += f"""'{public_email}'"""

        instruction += f""", {media_count}, {follower_count}, {following_count}, {past_profiles}, {is_profile_downloaded})"""

        dbCursor.execute(instruction) # Add the profile to the database
        dbCursor.execute(f"""INSERT INTO Highlight VALUES({pk}, {pk}, "Stories")""") # Add a default highlight for the stories (highlight_id = pk)
        connection.commit()

        profiles.append((pk, username, full_name, biography, is_private, media_count,
                         follower_count, following_count, past_profiles, is_profile_downloaded)) # Add the profile to the list as well
        listProfiles() # Update the screen

    except:
        print("There was an error!") # Couldn't add the profile

def getStories(username, highlight_id, highlight_title): # Gets the stories or highlights of the profile for download
    try:
        for profile in profiles:
            if profile[1] == username:
                pk = profile[0] # Find the pk of the given username
        
        if not os.path.exists(path + f"/{username}/Stories"):
            os.mkdir(path + f"/{username}/Stories")
        
        isHighlight = True
        if highlight_id == pk: # highlight_id = pk is for stories
            isHighlight = False

        if isHighlight: # Get the proper link according to being a story or highlight
            link = f"https://anonyig.com/api/ig/highlightStories/highlight:{highlight_id}"

        else:
            link = f"https://anonyig.com/api/ig/story?url=https://www.instagram.com/stories/{username}/"

        response = session.get(link) # Get the data
        if response.status_code != 200:
            return None # couldn't get the data
        
        result = dbCursor.execute(f"""SELECT * FROM Story WHERE pk = {pk}""")
        stories = result.fetchall() # Get the list of already downloaded stories from database
        
        newStories = [] # List of new stories that need to be downloaded

        data = json.loads(response.text)
        data = data['result']

        if len(data) == 0:
            return newStories # Return empty list
        
        for newStory in data:
            story_pk = int(newStory['pk'])
            downloaded = False

            for i in range(len(stories)):
                if stories[i][1] == story_pk: # Story already downloaded

                    if stories[i][2] == pk: # It was a story before
                        if isHighlight: # If now it's a highlight
                            files = glob.glob(path + f"/{username}/Stories/{story_pk}*")
                            if len(files) == 2: # Check if the files exist, if yes then copy them to the highlight folder
                                for file in files:
                                    if '/' in file:
                                        index = file.rindex("/")
                                    else:
                                        index = file.rindex("\\")
                                    shutil.copy(file, f"/{username}/Highlights/{highlight_title}_{highlight_id}/{file[index + 1:]}")

                                dbCursor.execute(f"""INSERT INTO Story VALUES({stories[i][0]},
                                                 {stories[i][1]}, {highlight_id}, {stories[i][3]})""") # Add the story to the database
                                # stories.append((stories[i][0], stories[i][1], highlight_id, stories[i][3]))
                                connection.commit()
                                downloaded = True

                        else: # If it hasn't changed then skip this
                            downloaded = True

                    elif stories[i][2] != highlight_id: # It's from another highlight
                        folders = glob.glob(path + f"/{username}/Highlights/*_{stories[i][2]}")
                        if len(folders) == 1:
                            files = glob.glob(folders[0] + f"/{story_pk}*")
                            if len(files) == 2: # Check if the files exist, if yes then copy them to the highlight folder
                                for file in files:
                                    if '/' in file:
                                            index = file.rindex("/")
                                    else:
                                        index = file.rindex("\\")
                                    
                                    if isHighlight:
                                        shutil.copy(file, path + f"/{username}/Highlights/{highlight_title}_{highlight_id}/{file[index + 1:]}")
                                    else:
                                        shutil.copy(file, path + f"/{username}/Stories/{file[index + 1:]}")
                                
                                dbCursor.execute(f"""INSERT INTO Story VALUES({stories[i][0]},
                                                 {stories[i][1]}, {highlight_id}, {stories[i][3]})""") # Add the story to the database
                                # stories.append((stories[i][0], stories[i][1], highlight_id, stories[i][3]))
                                connection.commit()
                                downloaded = True

                    else: # stories[i][2] == highlight.id (it's from the same highlight)
                        downloaded = True # Skip

                    break # One story with same story_pk is enough

            if downloaded:
                continue # It was found and copied so skip this one

            timestamp = newStory['taken_at']

            media_link = None
            if 'video_versions' in newStory.keys():
                media_link = newStory['video_versions'][0]['url']

            if media_link is None: # If story isn't video then get the best picture
                media_link = newStory['image_versions2']['candidates'][0]['url']

            thumbnail_link = newStory['image_versions2']['candidates'][-2]['url'] # 320 * 320 image for thumbnail

            if isHighlight: # Set the saving address according to being a story or highlight
                format = media_link[:media_link.index("?")]
                format = format[format.rindex("."):]
                media_address = f"/{username}/Highlights/{highlight_title}_{highlight_id}/{story_pk}{format}"

                format = thumbnail_link[:thumbnail_link.index("?")]
                format = format[format.rindex("."):]
                thumbnail_address = f"/{username}/Highlights/{highlight_title}_{highlight_id}/{story_pk}_thumbnail{format}"

            else:
                format = media_link[:media_link.index("?")]
                format = format[format.rindex("."):]
                media_address = f"/{username}/Stories/{story_pk}{format}"

                format = thumbnail_link[:thumbnail_link.index("?")]
                format = format[format.rindex("."):]
                thumbnail_address = f"/{username}/Stories/{story_pk}_thumbnail{format}"

            newStories.append((pk, story_pk, highlight_id, timestamp, media_link,
                               media_address, thumbnail_link, thumbnail_address)) # Add the story information to the list of new stories
        
        return newStories # Return the list of new stories
            

    except:
        return None # Something went wrong

def downloadStories(username, highlight_id, highlight_title): # Downloads the stories or highlights of the profile
    # Needs change for GUI implementation and multithreading
    newstories = getStories(username, highlight_id, highlight_title) # Get the list of new stories

    if newstories is None:
        print("There was an error!")
        return
    
    elif len(newstories) == 0:
        print("There was no story!")
        return

    for story in newstories:
        try:
            isDownloaded = tryDownloading(story[4], story[5]) # Try downloading the media
            if not isDownloaded:
                print("Couldn't download story!")
                continue
                    
            isDownloaded = tryDownloading(story[6], story[7]) # Try downloading the thumbnail
            if not isDownloaded:
                print("Couldn't download story!")
                continue
            
            dbCursor.execute(f"""INSERT INTO Story VALUES({story[0]}, {story[1]},
                             {story[2]}, {story[3]})""") # Add the story to the database
            # stories.append((story[0], story[1], story[2], story[3]))
            connection.commit()

        except:
            print("There was an error!")
            continue # Couldn't download, skip and try the next one

connection, dbCursor = initialize()

result = dbCursor.execute("""SELECT pk, username, full_name, biography, is_private, media_count,
                          follower_count, following_count, past_profiles, is_profile_downloaded FROM Profile""")
profiles = result.fetchall()