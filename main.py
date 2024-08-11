import sqlite3
from PIL import Image, ImageDraw, ImageFilter
import os
import shutil
import glob
from mimetypes import guess_extension, guess_type
import requests
import json

path = os.path.dirname(os.path.abspath(__file__)) + "/storage" # Base path
session = requests.Session() # Session for requests

def initialize(): # Initializes basic stuff
    try:
        if not os.path.exists(path):
            os.mkdir(path)
        
        initializeTables = False
        if not os.path.exists(path + "/data.db"):
            initializeTables = True

        connection = sqlite3.connect(path + "/data.db")
        dbCursor = connection.cursor()

        dbCursor.execute("PRAGMA foreign_keys = ON") # Enabling foreign key constraints

        if initializeTables:
            try:
                makeTables(dbCursor) # If tables are not created, create them
            except:
                os.remove(path + "/data.db") # If there was an error then remove the database
                return None, None
            
        return connection, dbCursor
    except:
        return None, None

def makeTables(dbCursor): # Creates tables
    dbCursor.execute("""CREATE TABLE Profile(pk PRIMARY KEY, username, full_name,
                     page_name, biography, is_private, public_email, media_count,
                     follower_count, following_count, profile_id)""")
    
    dbCursor.execute("""CREATE TABLE Post(pk, link, number_of_items, caption, timestamp, isTag,
                     PRIMARY KEY(pk, link), FOREIGN KEY(pk) REFERENCES Profile(pk))""")

    dbCursor.execute("""CREATE TABLE Highlight(highlight_id PRIMARY KEY, pk, title,
                     number_of_items, FOREIGN KEY(pk) REFERENCES Profile(pk))""")
    
    dbCursor.execute("""CREATE TABLE Story(pk, story_pk, highlight_id, timestamp, PRIMARY KEY(pk, story_pk, highlight_id),
                     FOREIGN KEY(pk) REFERENCES Profile(pk), FOREIGN KEY(highlight_id) REFERENCES Highlight(highlight_id))""")
    
    dbCursor.execute("""CREATE TABLE ProfileHistory(pk, profile_id,
                     PRIMARY KEY(pk, profile_id), FOREIGN KEY(pk) REFERENCES Profile(pk))""")

def makeThumbnail(address, size): # Makes a thumbnail for given image and saves it
    try:
        file = glob.glob(path + address + ".*")
        if len(file) != 1:
            return False # Couldn't find the image
        file = file[0]
        
        image = Image.open(file)
        resized_image = image.resize((size, size)) # Thumbnail size

        blur_radius = 2 # Radius of blurring the edges of the circle thumbnail
        offset = blur_radius * 2
        mask = Image.new("L", resized_image.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((offset, offset, resized_image.size[0] - offset, resized_image.size[1] - offset), fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(blur_radius))

        resized_image.putalpha(mask) # Making the edges transparent

        resized_image.save(file[:file.rindex('.')] + "_thumbnail.png") # Saving thumbnail at the same path
        
        return True
    
    except:
        return False # Couldn't make the thumbnail

def guessType(file): # Guesses the type of the file
    mimestart = guess_type(path + file)[0] # Guessing the type of the file

    if mimestart != None:
        mimestart = mimestart.split('/')[0]

        if mimestart in ['image', 'video']:
            return mimestart
        
    return 'None' # Couldn't guess or it wasn't image or video

def downloadLink(link, address): # Downloads the link and saves it to the address
    # TODO: Needs change for GUI implementation and multithreading
    try:
        media = session.get(link, allow_redirects=True, timeout=60) # Get the media from the link

        extension = guess_extension(media.headers['content-type'].partition(';')[0].strip()) # Find the extension from the headers
        if extension is None: # If couldn't find from headers then find from the link
            extension = link[:link.index('?')]
            extension = extension[extension.rindex('.'):]

        open(path + address + extension, 'wb').write(media.content) # saving the file
        return True
    
    except:
        return False # Couldn't download the link

def tryDownloading(link, address): # Tries to download the link for 5 times
    isDownloaded = downloadLink(link, address) # Try downloading the link
    if not isDownloaded: # If couldn't download the link, Try 5 more times
        for i in range(5):
            isDownloaded = downloadLink(link, address) # Try downloading the link
            if isDownloaded:
                return True

        if not isDownloaded:
            return False # Couldn't download the link
        
    return True

def listProfiles(): # Lists the profiles
    # TODO: Needs change for GUI implementation
    try:
        if os.name == 'nt': # Clearing the screen
            os.system('cls')

        else:
            os.system('clear')
        
        result = dbCursor.execute("""SELECT username, full_name, biography, media_count,
                                follower_count, following_count FROM Profile""")
        profiles = result.fetchall() # Get the list of profiles

        for profile in profiles:
            biography = profile[2]
            if biography is None:
                biography = ''

            print(profile[0] + ":\n" + profile[1] + "\n" + biography + "\nPosts: " + str(profile[3])
                + "\nFollowers: " + str(profile[4]) + "\nFollowings: " + str(profile[5])) # Show the details of each profile
            print("---------------------------------")
    
    except:
        print("Couldn't list the profiles!") # There was an error somewhere

def getProfileData(username): # Get a profile's data
    try:
        response = session.get(f'https://anonyig.com/api/ig/userInfoByUsername/{username}')
        if response.status_code != 200:
            return None # couldn't get the data
        
        data = json.loads(response.text)
        data = data['result']['user']

        profile = {
            'pk': int(data["pk"]),
            'username': data["username"],
            'full_name': data["full_name"],
            'page_name': data["page_name"],
            'biography': data["biography"],
        }

        is_private = data["is_private"]
        if is_private:
            is_private = 1
        else:
            is_private = 0
        
        profile['is_private'] = is_private

        if "public_email" in data.keys():
            public_email = data["public_email"]

            if public_email == '':
                public_email = None

        else:
            public_email = None

        profile['public_email'] = public_email
        profile['media_count'] = data["media_count"]
        profile['follower_count'] = data["follower_count"]
        profile['following_count'] = data["following_count"]

        if "profile_pic_id" in data.keys():
            profile_id = data["profile_pic_id"]
            profile_id = int(profile_id[:profile_id.index('_')])
        
        else:
            profile_id = profile['pk']

        profile['profile_id'] = profile_id
        profile['original_profile_pic_link'] = data["hd_profile_pic_url_info"]["url"]
        profile['original_profile_pic'] = f"/{username}/Profiles/Profile"

        return profile # return profile's data

    except:
        return None # couldn't get the data

def addProfile(username): # Adds a profile
    try:
        result = dbCursor.execute(f"""SELECT * FROM Profile WHERE username = '{username}'""")
        doesExist = result.fetchall() # Get the username information

        if len(doesExist) != 0:
            print("This account is already added!")
            return # profile already exist, don't need to continue
        
        data = getProfileData(username) # Get the profile's data
        if data is None:
            print("There was an error!")
            return # couldn't get the data
        
        if not os.path.exists(path + f"/{data['username']}"): # Make the folders for the profile
            os.mkdir(path + f"/{data['username']}")
        
        if not os.path.exists(path + f"/{data['username']}/Profiles"):
            os.mkdir(path + f"/{data['username']}/Profiles")

        isDownloaded = tryDownloading(data['original_profile_pic_link'], data['original_profile_pic']) # Try downloading the profile picture
        if not isDownloaded:
            print("There was an error!")
            return

        if not makeThumbnail(data['original_profile_pic'], 128): # Try Making a thumbnail for the profile picture
            print("There was an error!")
            return

        instruction = f"""INSERT INTO Profile VALUES({data['pk']}, "{data['username']}", "{data['full_name']}","""

        if data['page_name'] is None:
            instruction += "NULL"
        else:
            instruction += f"""'{data['page_name']}'"""
        
        if data['biography'] == '':
            instruction += f", NULL"
            data['biography'] = None
        else:
            instruction += f""", '{data['biography']}'"""

        instruction += f""", {data['is_private']},"""

        if data['public_email'] is None:
            instruction += "NULL"
        else:
            instruction += f"""'{data['public_email']}'"""

        instruction += f""", {data['media_count']}, {data['follower_count']}, {data['following_count']},
                        {data['profile_id']})"""

        dbCursor.execute(instruction) # Add the profile to the database
        dbCursor.execute(f"""INSERT INTO Highlight VALUES({data['pk']}, {data['pk']},
                         "Stories", 0)""") # Add a default highlight for the stories (highlight_id = pk)
        connection.commit()
        
        if not data['is_private']:
            updateHighlights(data['pk'], data['username']) # If the account isn't private then update it's highlights

        listProfiles() # Update the screen

    except:
        connection.rollback() # Rollback the changes
        print("There was an error!") # Couldn't add the profile

def addProfileHistory(username, profile_id): # Add a profile pic to history
    try:
        if not os.path.exists(path + f"/{username}/Profiles"):
            os.mkdir(path + f"/{username}/Profiles")
        
        else: # If Profiles folder exist then move the past profile files (if any) to History folder
            if not os.path.exists(path + f"/{username}/Profiles/History"):
                os.mkdir(path + f"/{username}/Profiles/History")
            
            files = glob.glob(path + f"/{username}/Profiles/Profile*.*")

            for file in files:
                newName = file.rsplit("Profile", 1)
                newName = newName[0] + f"/History/{profile_id}/" + newName[1] # Change the name from Profile(_thumbnail) to {profile_id}

                shutil.move(file, newName) # Move the file to the History folder

        return True # Profile added to history
    
    except:
        return False # Couldn't add profile to history

def updateProfile(username, withHighlights = True): # Updates the profile
    try:
        result = dbCursor.execute(f"""SELECT is_private, profile_id FROM Profile WHERE username = '{username}'""")
        user_data = result.fetchone() # Get current information of user

        new_data = getProfileData(username) # Get new information of user
        if new_data is None:
            print("Couldn't update profile")
            return False
        
        if user_data[1] != new_data['profile_id']: # Profile picture has changed
            if not addProfileHistory(username, user_data[1]):
                print("Couldn't update profile")
                return False
            
        isDownloaded = tryDownloading(new_data['original_profile_pic_link'], new_data['original_profile_pic']) # Try downloading the profile picture
        if not isDownloaded:
            print("Couldn't update profile")
            return False

        if not makeThumbnail(new_data['original_profile_pic'], 128): # Try Making a thumbnail for the profile picture
            print("Couldn't update profile")
            return False
        
        instruction = f"""UPDATE Profile SET full_name = "{new_data['full_name']}", page_name = """

        if new_data['page_name'] is None:
            instruction += "NULL"
        else:
            instruction += f"""'{new_data['page_name']}'"""
        
        instruction += ", biography = "
        
        if new_data['biography'] == '':
            instruction += f"NULL"
            new_data['biography'] = None
        else:
            instruction += f"""'{new_data['biography']}'"""

        instruction += f""", is_private = {new_data['is_private']}, public_email = """

        if new_data['public_email'] is None:
            instruction += "NULL"
        else:
            instruction += f"""'{new_data['public_email']}'"""

        instruction += f""", media_count = {new_data['media_count']}, follower_count = {new_data['follower_count']},
                        following_count = {new_data['following_count']}, profile_id = {new_data['profile_id']}
                        WHERE pk = {new_data['pk']}"""
        
        dbCursor.execute(instruction) # Update profile's information in database

        if user_data[1] != new_data['profile_id']: # Profile picture has changed
            dbCursor.execute(f"""INSERT INTO ProfileHistory VALUES({new_data['pk']},
                             {user_data[1]})""") # Add the past profile to history
        
        connection.commit()

        if withHighlights and (not new_data['is_private']):
            updateHighlights(new_data['pk'], new_data['username']) # If the account isn't private then update it's highlights

        listProfiles() # Update the screen

        return True # Profile updated successfully
        
    except:
        connection.rollback() # Rollback the changes
        print("Couldn't update profile")
        return False # Threre was an error somewhere

def checkDuplicateStories(pk, username, story_pk, highlight_id, highlight_title, stories): # Check if the story is already downloaded
    try:
        isHighlight = pk != highlight_id # highlight_id = pk is for stories

        for i in range(len(stories)):
            if stories[i][1] == story_pk: # Story already downloaded
                
                if stories[i][2] == pk: # It was a story before
                    if isHighlight: # If now it's a highlight
                        try:
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
                                connection.commit()
                                return True
                        
                        except:
                            connection.rollback() # Rollback the changes
                            return False # Something went wrong but we know it's not from the same highlight

                    else: # If it hasn't changed then skip this
                        return True

                elif stories[i][2] != highlight_id: # It's from another highlight
                    try:
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
                                connection.commit()
                                return True
                            
                    except:
                        connection.rollback() # Rollback the changes
                        return False # Something went wrong but we know it's not from the same highlight

                else: # stories[i][2] == highlight.id (it's from the same highlight)
                    return True # Skip

                break # One story with same story_pk is enough
        
        return False # Couldn't find the story
    
    except:
        connection.rollback() # Rollback the changes
        return None # Something went wrong

def getStories(pk, username, highlight_id, highlight_title): # Gets the stories or highlights of the profile for download
    try:
        number_of_items = 0 # Number of items in the stories or highlights

        isHighlight = pk != highlight_id # highlight_id = pk is for stories

        if isHighlight: # Get the proper link according to being a story or highlight
            link = f"https://anonyig.com/api/ig/highlightStories/highlight:{highlight_id}"

        else:
            link = f"https://anonyig.com/api/ig/story?url=https://www.instagram.com/stories/{username}/"

        response = session.get(link) # Get the data
        if response.status_code != 200:
            return None, number_of_items # Couldn't get the data
        
        newStories = [] # List of new stories that need to be downloaded

        data = json.loads(response.text)
        data = data['result']
        number_of_items = len(data)

        if number_of_items == 0:
            return newStories, number_of_items # Return empty list if there is no story
        
        result = dbCursor.execute(f"""SELECT * FROM Story WHERE pk = {pk}""")
        stories = result.fetchall() # Get the list of already downloaded stories from database
        
        for newStory in data:
            story_pk = int(newStory['pk'])
            downloaded = checkDuplicateStories(pk, username, story_pk, highlight_id, highlight_title, stories) # Check if the story is already downloaded

            if downloaded or (downloaded is None):
                continue # It was (found and copied) or (couldn't check and it may be duplicate) so skip this one

            timestamp = newStory['taken_at']

            media_link = None
            if 'video_versions' in newStory.keys():
                media_link = newStory['video_versions'][0]['url']

            if media_link is None: # If story isn't video then get the best picture
                media_link = newStory['image_versions2']['candidates'][0]['url']

            thumbnail_link = newStory['image_versions2']['candidates'][-2]['url'] # 320 * 320 image for thumbnail

            if isHighlight: # Set the saving address according to being a story or highlight
                media_address = f"/{username}/Highlights/{highlight_title}_{highlight_id}/{story_pk}"

                thumbnail_address = f"/{username}/Highlights/{highlight_title}_{highlight_id}/{story_pk}_thumbnail"

            else:
                media_address = f"/{username}/Stories/{story_pk}"

                thumbnail_address = f"/{username}/Stories/{story_pk}_thumbnail"

            newStories.append((pk, story_pk, highlight_id, timestamp, media_link,
                               media_address, thumbnail_link, thumbnail_address)) # Add the story information to the list of new stories
        
        return newStories, number_of_items # Return the list of new stories and the number of items
            
    except:
        return None, number_of_items # Something went wrong

def downloadStories(pk, username, highlight_id, highlight_title): # Downloads the stories or highlights of the profile
    # TODO: Needs change for GUI implementation and multithreading
    newstories, number_of_items = getStories(pk, username, highlight_id, highlight_title) # Get the list of new stories and the number of items

    if newstories is None:
        print("There was an error!")
        return number_of_items # At least return the number of items
    
    elif len(newstories) == 0:
        print("There was no story!")
        return number_of_items # If there is no story then just return the number of items

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
            connection.commit()

        except:
            connection.rollback() # Rollback the changes
            print("There was an error!")
            continue # Couldn't download, skip and try the next one
    
    return number_of_items # Return the number of items

def getHighlightsData(pk): # Get the highlights data of the profile
    try:
        response = session.get(f'https://anonyig.com/api/ig/highlights/{pk}') # Get highlights information

        if response.status_code != 200: # Couldn't get the highlights data
            return None
        
        data = json.loads(response.text)
        data = data['result']

        return data # Return the highlights data
    
    except:
        return None # Couldn't get the highlights data

def updateSingleHighlight(pk, username, newHighlight, highlights): # Updates a single highlight
    try:
        highlight_id = newHighlight['id']
        highlight_id = int(highlight_id[highlight_id.index(":") + 1:])

        title = newHighlight['title']
        cover_link = newHighlight['cover_media']['cropped_image_version']['url']

        folder = glob.glob(path + f"/{username}/Highlights/*_{highlight_id}") # Check if the highlight folder already exists

        for i in range(len(highlights)):
            if highlights[i][0] == highlight_id: # If highlight already exists

                if (highlights[i][2] == title): # If title hasn't changed
                    if (len(folder) == 0): # And folder doesn't exist
                        os.mkdir(path + f"/{username}/Highlights/{title}_{highlight_id}")

                else:

                    if len(folder) > 0: # If folder exists then rename it
                        for i in folder[1:]:
                            shutil.copytree(i, folder[0], dirs_exist_ok=True) # Copy the files from the other folders to the first one
                            shutil.rmtree(i) # Remove the other folders
                        
                        os.rename(folder[0], path + f"/{username}/Highlights/{title}_{highlight_id}") # Rename the folder
                        
                    else:
                        os.mkdir(path + f"/{username}/Highlights/{title}_{highlight_id}")
                    
                    try:
                        dbCursor.execute(f"""UPDATE Highlight SET title = "{title}"
                                        WHERE highlight_id = {highlight_id}""") # Update the title
                        connection.commit()
                    
                    except:
                        connection.rollback() # Rollback the changes
                        return True # Couldn't Update the database but the folder is updated at least
                
                isDownloaded = tryDownloading(cover_link, f"/{username}/Highlights/{title}_{highlight_id}/Cover") # Try downloading highlight's cover
                # TODO: The cover may be missing (should use the first highlight instead)
                if isDownloaded:
                    makeThumbnail(f"/{username}/Highlights/{title}_{highlight_id}/Cover", 64) # Make thumbnail for cover

                del(highlights[i])
                return True # Highlight was found and updated
        
        # If this highlight is new
        if len(folder) == 0:
            os.mkdir(path + f"/{username}/Highlights/{title}_{highlight_id}")

        else:
            for i in folder[1:]:
                shutil.copytree(i, folder[0], dirs_exist_ok=True) # Copy the files from the other folders to the first one
                shutil.rmtree(i) # Remove the other folders
            
            os.rename(folder[0], path + f"/{username}/Highlights/{title}_{highlight_id}")
        
        dbCursor.execute(f"""INSERT INTO Highlight VALUES({highlight_id}, {pk}, "{title}", 0)""") # Add it to database
        connection.commit()

        isDownloaded = tryDownloading(cover_link, f"/{username}/Highlights/{title}_{highlight_id}/Cover") # Try downloading highlight's cover
        # TODO: The cover may be missing (should use the first highlight instead)
        if isDownloaded:
            makeThumbnail(f"/{username}/Highlights/{title}_{highlight_id}/Cover", 64) # Make thumbnail for the cover
        
        return True # Highlight was added

    except:
        connection.rollback() # Rollback the changes
        return False # There was an error somewhere

def updateHighlights(pk, username): # Updates the highlights of the profile
    try:
        data = getHighlightsData(pk) # Get the highlights data
        update_states = [] # Stores the update states of highlights

        if data is None: # Couldn't get the highlights data
            print("Couldn't get the highlights!")
            return False, [data, update_states] # Couldn't get the highlights data

        if not os.path.exists(path + f"/{username}/Highlights"):
            os.mkdir(path + f"/{username}/Highlights") # Make Highlights folder
        
        result = dbCursor.execute(f"""SELECT * FROM Highlight WHERE pk = {pk}""")
        highlights = result.fetchall() # Get the list of highlights from database

        for newHighlight in data:
            update_states.append(updateSingleHighlight(pk, username, newHighlight, highlights)) # Update this highlight

        return True, [data, update_states] # Return the highlights data and update states

    except:
        print("Couldn't get the highlights!")
        return False, [data, update_states] # Couldn't update the highlights

def downloadSingleHighlightStories(username, highlight_id, direct_call = True): # Downloads the stories of a single highlight
    try:
        if direct_call:
            updated = updateProfile(username, False) # Update the profile
            if not updated:
                print("Couldn't update the profile!")
        
        result = dbCursor.execute(f"""SELECT pk, is_private FROM Profile WHERE username = '{username}'""")
        pk, is_private = result.fetchone() # Get the pk and is_private of the profile

        if is_private == 1: # If the account is private
            print("This account is private!")
            return

        if pk == highlight_id: # If the highlight is the stories
            if not os.path.exists(path + f"/{username}/Stories"):
                os.mkdir(path + f"/{username}/Stories") # Make Stories folder
        
        elif direct_call: # If the highlight is a highlight and it's a direct call
            if not os.path.exists(path + f"/{username}/Highlights"):
                os.mkdir(path + f"/{username}/Highlights") # Make Highlights folder
        
        if direct_call and pk != highlight_id: # If the highlight is a highlight
            data = getHighlightsData(pk) # Get the highlights data

            if data is None: # Couldn't get the highlights data
                print("Couldn't update the highlight!")
                return
            
            for highlight in data:
                if highlight['id'] == f"highlight:{highlight_id}":
                    new_data = highlight
                    break
            else: # Couldn't find the highlight_id in the data
                print("Couldn't update the highlight!")
                return
            
            result = dbCursor.execute(f"""SELECT * FROM Highlight WHERE pk = {pk}""")
            highlights = result.fetchall() # Get the list of highlights from database

            state = updateSingleHighlight(pk, username, new_data, highlights) # Update this highlight

            if not state: # Couldn't update the highlight
                print("Couldn't update the highlight!")
                return
        
        number_of_items = downloadStories(pk, username, highlight_id, highlight['title']) # Download the stories of the highlight

        try:
            if number_of_items > 0: # If there was any story
                result = dbCursor.execute(f"""SELECT number_of_items FROM Highlight WHERE highlight_id = {highlight_id}""")
                old_number_of_items = result.fetchone()[0] # Get the old number of items
                
                result = dbCursor.execute(f"""SELECT count(*) FROM Story WHERE pk = {pk} AND highlight_id = {highlight_id}""")
                number_of_downloaded = result.fetchone()[0] # Get the number of downloaded stories

                new_max = max(number_of_items, number_of_downloaded) # Get the new maximum number of items

                if new_max > old_number_of_items: # If the new maximum is greater than the old maximum
                    dbCursor.execute(f"""UPDATE Highlight SET number_of_items = {new_max}
                                    WHERE highlight_id = {highlight_id}""")
                    connection.commit() # Update the number of items in the database

        except: # Couldn't update the number of items
            pass

    except:
        print("Couldn't download the highlight!")
        return # There was an error somewhere

connection, dbCursor = initialize() # Initialize the program

if connection is None: # If there was an error in initializing
    print("Couldn't initialize the program!")
    exit() # Exit the program