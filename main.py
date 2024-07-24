import sqlite3
import os
import shutil
import glob
import mimetypes
mimetypes.init()
import requests
import json

path = os.path.dirname(os.path.abspath(__file__)) + "/storage"
session = requests.Session()

def initialize():
    if not os.path.exists(path):
        os.mkdir(path)
    
    initializeTables = False
    if not os.path.exists(path + "/data.db"):
        initializeTables = True

    connection = sqlite3.connect(path + "/data.db")
    dbCursor = connection.cursor()

    dbCursor.execute("PRAGMA foreign_keys = ON")

    if initializeTables:
        makeTables(dbCursor)
    return connection, dbCursor

def makeTables(dbCursor):
    dbCursor.execute("""CREATE TABLE Profile(pk PRIMARY KEY, username, full_name,
                     page_name, biography, is_private, public_email, media_count,
                     follower_count, following_count, past_profiles, is_profile_downloaded)""")
    
    dbCursor.execute("""CREATE TABLE Post(pk, link, number_of_items, caption, timestamp, isTag,
                     PRIMARY KEY(pk, link), FOREIGN KEY(pk) REFERENCES Profile(pk))""")

    dbCursor.execute("""CREATE TABLE Highlight(highlight_id, pk, title, PRIMARY KEY(highlight_id),
                     FOREIGN KEY(pk) REFERENCES Profile(pk))""")
    
    dbCursor.execute("""CREATE TABLE Story(pk, story_pk, highlight_id, timestamp, PRIMARY KEY(pk, story_pk, highlight_id),
                     FOREIGN KEY(pk) REFERENCES Profile(pk), FOREIGN KEY(highlight_id) REFERENCES Highlight(highlight_id))""")

def guessType(fileName):
    mimestart = mimetypes.guess_type(fileName)[0]

    if mimestart != None:
        mimestart = mimestart.split('/')[0]

        if mimestart == 'image':
            return 'Photo'
        elif mimestart == 'video':
            return 'Video'
        
    return 'None'

def downloadLink(link, address):
    # Needs change for GUI implementation and multithreading
    try:
        media = requests.get(link, allow_redirects=True)
        open(path + address, 'wb').write(media.content)
        return True
    except:
        return False

def tryDownloading(link, address):
    isDownloaded = downloadLink(link, address)
    if not isDownloaded:
        for i in range(5):
            isDownloaded = downloadLink(link, address)
            if isDownloaded:
                return True

        if not isDownloaded:
            return False
        
    return True

def listProfiles():
    # Needs change for GUI implementation
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')
    for profile in profiles:
        print(profile[1] + ":\n" + profile[2] + "\n" + profile[3] + "\nPosts: " + str(profile[5])
              + "\nFollowers: " + str(profile[6]) + "\nFollowings: " + str(profile[7]))
        print("---------------------------------")

def addProfile(username):
    try:
        for profile in profiles:
            if profile[1] == username:
                print("This account is already added!")
                return
        
        response = session.get(f'https://anonyig.com/api/ig/userInfoByUsername/{username}')
        if response.status_code != 200:
            print("There was an error!")
            return
        
        data = json.loads(response.text)
        data = data['result']['user']
        
        if not os.path.exists(path + f"/{username}"):
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
        small_profile_pic = f"/{username}/Profiles/Profile_thumbnail{format}"
        past_profiles = 0
        is_profile_downloaded = 0

        isDownloaded = tryDownloading(original_profile_pic_link, original_profile_pic)
        if not isDownloaded:
            print("There was an error!")
            return

        if data["has_anonymous_profile_picture"] == True:
            shutil.copyfile(original_profile_pic, small_profile_pic)
        else:
            small_profile_pic_link = data["hd_profile_pic_versions"][0]["url"]
            format = original_profile_pic_link[:original_profile_pic_link.index("?")]
            format = format[format.rindex("."):]
            small_profile_pic = f"/{username}/Profiles/Profile_thumbnail{format}"

            isDownloaded = tryDownloading(small_profile_pic_link, small_profile_pic)
            if not isDownloaded:
                print("There was an error!")
                return

        instruction = f"""INSERT INTO Profile VALUES({pk}, "{username}", "{full_name}","""
        if page_name is None:
            instruction += "NULL"
        else:
            instruction += f"""'{page_name}'"""
        instruction += f""", "{biography}", {is_private},"""
        if public_email is None:
            instruction += "NULL"
        else:
            instruction += f"""'{public_email}'"""
        instruction += f""", {media_count}, {follower_count}, {following_count}, {past_profiles}, {is_profile_downloaded})"""

        dbCursor.execute(instruction)
        dbCursor.execute(f"""INSERT INTO Highlight VALUES({pk}, {pk}, "Stories")""")
        connection.commit()

        profiles.append((pk, username, full_name, biography, is_private, media_count,
                         follower_count, following_count, past_profiles, is_profile_downloaded))
        listProfiles()

    except:
        print("There was an error!")

def getStories(username, highlight_id, highlight_title):
    try:
        for profile in profiles:
            if profile[1] == username:
                pk = profile[0]
        
        if not os.path.exists(path + f"/{username}/Stories"):
            os.mkdir(path + f"/{username}/Stories")
        
        isHighlight = True
        if highlight_id == pk:
            isHighlight = False

        if isHighlight:
            link = f"https://anonyig.com/api/ig/highlightStories/highlight:{highlight_id}"
        else:
            link = f"https://anonyig.com/api/ig/story?url=https://www.instagram.com/stories/{username}/"
        response = session.get(link)
        if response.status_code != 200:
            return None
        
        result = dbCursor.execute(f"""SELECT * FROM Story WHERE pk = {pk}""")
        stories = result.fetchall()
        
        newStories = []

        data = json.loads(response.text)
        data = data['result']
        if len(data) == 0:
            return newStories
        
        for newStory in data:
            story_pk = int(newStory['pk'])
            downloaded = False

            for i in range(len(stories)):
                if stories[i][1] == story_pk:

                    if stories[i][2] == pk:
                        if isHighlight:
                            files = glob.glob(path + f"/{username}/Stories/{story_pk}*")
                            if len(files) == 2:
                                for file in files:
                                    if '/' in file:
                                        index = file.rindex("/")
                                    else:
                                        index = file.rindex("\\")
                                    shutil.copy(file, f"/{username}/Highlights/{highlight_title}_{highlight_id}/{file[index + 1:]}")

                                dbCursor.execute(f"""INSERT INTO Story VALUES({stories[i][0]},
                                                 {stories[i][1]}, {highlight_id}, {stories[i][3]})""")
                                # stories.append((stories[i][0], stories[i][1], highlight_id, stories[i][3]))
                                connection.commit()
                                downloaded = True

                        else:
                            downloaded = True

                    elif stories[i][2] != highlight_id:
                        folders = glob.glob(path + f"/{username}/Highlights/*_{stories[i][2]}")
                        if len(folders) == 1:
                            files = glob.glob(folders[0] + f"/{story_pk}*")
                            if len(files) == 2:
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
                                                 {stories[i][1]}, {highlight_id}, {stories[i][3]})""")
                                # stories.append((stories[i][0], stories[i][1], highlight_id, stories[i][3]))
                                connection.commit()
                                downloaded = True

                    else:
                        downloaded = True

                    break

            if downloaded:
                continue

            timestamp = newStory['taken_at']

            media_link = None
            if 'video_versions' in newStory.keys():
                media_link = newStory['video_versions'][0]['url']

            if media_link is None:
                media_link = newStory['image_versions2']['candidates'][0]['url']

            thumbnail_link = newStory['image_versions2']['candidates'][-3]['url']

            if isHighlight:
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
                               media_address, thumbnail_link, thumbnail_address))
        
        return newStories
            

    except:
        return None

def downloadStories(username, highlight_id, highlight_title):
    # Needs change for GUI implementation and multithreading
    newstories = getStories(username, highlight_id, highlight_title)
    if newstories is None:
        print("There was an error!")
        return
    
    elif len(newstories) == 0:
        print("There was no story!")
        return

    for story in newstories:
        try:
            isDownloaded = tryDownloading(story[4], story[5])
            if not isDownloaded:
                print("Couldn't download story!")
                continue
                    
            isDownloaded = tryDownloading(story[6], story[7])
            if not isDownloaded:
                print("Couldn't download story!")
                continue
            
            dbCursor.execute(f"""INSERT INTO Story VALUES({story[0]}, {story[1]}, {story[2]}, {story[3]})""")
            # stories.append((story[0], story[1], story[2], story[3]))
            connection.commit()

        except:
            print("There was an error!")
            continue

connection, dbCursor = initialize()

result = dbCursor.execute("""SELECT pk, username, full_name, biography, is_private, media_count,
                          follower_count, following_count, past_profiles, is_profile_downloaded FROM Profile""")
profiles = result.fetchall()