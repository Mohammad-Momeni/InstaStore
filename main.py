import sqlite3
from PIL import Image, ImageDraw, ImageFilter
import os
import shutil
import glob
from time import sleep, time
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

def circleCrop(image): # Crops the image to a circle
    blur_radius = 2 # Radius of blurring the edges of the circle thumbnail
    offset = blur_radius * 2

    mask = Image.new("L", image.size, 0) # Creating a mask for the image

    draw = ImageDraw.Draw(mask)
    draw.ellipse((offset, offset, image.size[0] - offset, image.size[1] - offset), fill=255) # Drawing the circle on the mask

    mask = mask.filter(ImageFilter.GaussianBlur(blur_radius)) # Blurring the edges of the circle

    image.putalpha(mask) # Applying the mask to the image
    
def makeThumbnail(address, size, circle = False): # Makes a thumbnail for given image and saves it
    try:
        file = glob.glob(path + address + ".*")
        if len(file) != 1:
            return False # Couldn't find the image
        file = file[0]
        
        image = Image.open(file) # Open the image

        if image.height != image.width: # If the image isn't square
            square_size = min(image.height, image.width) # Get the minimum size

            height_offset = (image.height - square_size) // 2 # Get the offset for height
            width_offset = (image.width - square_size) // 2 # Get the offset for width

            image = image.crop((width_offset, height_offset, width_offset + square_size, height_offset + square_size)) # Crop the image to make it square

        resized_image = image.resize((size, size)) # Resize the image to the thumbnail size

        if circle: # If the thumbnail should be a circle
            circleCrop(resized_image) # Cropping the thumbnail to a circle

        resized_image.save(file[:file.rindex('.')] + "_thumbnail.png") # Saving thumbnail at the same path
        
        return True # Thumbnail made successfully
    
    except:
        return False # Couldn't make the thumbnail

def guessType(file): # Guesses the type of the file
    mimestart = guess_type(path + file)[0] # Guessing the type of the file

    if mimestart != None:
        mimestart = mimestart.split('/')[0]

        if mimestart in ['image', 'video']:
            return mimestart
        
    return 'None' # Couldn't guess or it wasn't image or video

def sendRequest(url, timeout = 60, retries = 3): # Sends a request to the url and returns the response
    try:
        response = session.get(url, timeout=timeout) # Sending the request
        
        if response.status_code == 200:
            return response # Return the response
        
        elif (response.status_code) == 429 and (retries > 0): # Too many requests
            sleep(60) # Sleep for a minute

            return sendRequest(url, retries - 1) # Try again
        
        else:
            return None # Couldn't get the data
    
    except:
        return None # Couldn't get the data

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

def tryDownloading(link, address, retries = 3): # Tries to download the link for retries times
    isDownloaded = downloadLink(link, address) # Try downloading the link
    if not isDownloaded: # If couldn't download the link, Try 5 more times
        for i in range(retries):
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

def moveProfileHistory(username, profile_id): # Moves the past profile files (if any) to History folder 
    try:
        files = glob.glob(path + f"/{username}/Profiles/Profile*.*") # Get the profile files

        if len(files) == 0:
            return True # No profile files to move
        
        if not os.path.exists(path + f"/{username}/Profiles/History"): # Make the History folder
            os.mkdir(path + f"/{username}/Profiles/History")

        for file in files:
            newName = file.rsplit("Profile", 1)
            newName = newName[0] + f"/History/{profile_id}" + newName[1] # Change the name from Profile(_thumbnail) to {profile_id}

            shutil.move(file, newName) # Move the file to the History folder

        return True # Profile moved to history successfully
    
    except:
        return False # Couldn't move the profile to history

def getProfileData(username): # Get a profile's data
    try:
        response = sendRequest(f'https://anonyig.com/api/ig/userInfoByUsername/{username}') # Get the profile's data
        if response is None:
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
        
        if not os.path.exists(path + f"/{data['username']}"): # Make the profile folder
            os.mkdir(path + f"/{data['username']}")
        
        if not os.path.exists(path + f"/{data['username']}/Profiles"): # Make the Profiles folder
            os.mkdir(path + f"/{data['username']}/Profiles")
        
        # Else if Profiles folder exist then move the past profile files (if any) to History folder
        elif not moveProfileHistory(data['username'], int(time())):
            print("Couldn't Move the past profile to history!")
            return

        isDownloaded = tryDownloading(data['original_profile_pic_link'], data['original_profile_pic']) # Try downloading the profile picture
        if not isDownloaded:
            print("There was an error!")
            return

        if not makeThumbnail(data['original_profile_pic'], 128, True): # Try Making a thumbnail for the profile picture
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

def updateProfile(username, withHighlights = True): # Updates the profile
    try:
        result = dbCursor.execute(f"""SELECT is_private, profile_id FROM Profile WHERE username = '{username}'""")
        user_data = result.fetchone() # Get current information of user

        new_data = getProfileData(username) # Get new information of user
        if new_data is None:
            print("Couldn't update profile")
            return False
        
        if not os.path.exists(path + f"/{username}/Profiles"): # Make the Profiles folder
            os.mkdir(path + f"/{username}/Profiles")
        
        elif user_data[1] != new_data['profile_id']: # Profile picture has changed
            if not moveProfileHistory(username, user_data[1]): # Move the past profile to history
                print("Couldn't update profile")
                return False
            
        isDownloaded = tryDownloading(new_data['original_profile_pic_link'], new_data['original_profile_pic']) # Try downloading the profile picture
        if not isDownloaded:
            print("Couldn't update profile")
            return False

        if not makeThumbnail(new_data['original_profile_pic'], 128, True): # Try Making a thumbnail for the profile picture
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
        result = dbCursor.execute(f"""SELECT * FROM Story WHERE pk = {pk} AND
                                  story_pk = {story_pk} AND highlight_id = {highlight_id}""")
        same_story = result.fetchone() # Check if the story is already downloaded

        if same_story is not None: # An story with same story_pk and highlight_id is already downloaded
            return True # Story already downloaded
        
        isHighlight = pk != highlight_id # highlight_id = pk is for stories

        for i in range(len(stories)):
            if stories[i][1] == story_pk: # Story already downloaded
                
                if stories[i][2] == pk: # It was a story before and now it's a highlight
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

                else: # It's from another highlight
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

        response = sendRequest(link) # Get the data
        if response is None:
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
        response = sendRequest(f'https://anonyig.com/api/ig/highlights/{pk}') # Get highlights information

        if response is None: # Couldn't get the highlights data
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
                    makeThumbnail(f"/{username}/Highlights/{title}_{highlight_id}/Cover", 64, True) # Make thumbnail for cover

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
            makeThumbnail(f"/{username}/Highlights/{title}_{highlight_id}/Cover", 64, True) # Make thumbnail for the cover
        
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
            return data, update_states # Return None and empty list
        
        if len(data) == 0: # If there is no highlight
            print("There is no highlight!")
            return data, update_states # Return the highlights data and empty list

        if not os.path.exists(path + f"/{username}/Highlights"):
            os.mkdir(path + f"/{username}/Highlights") # Make Highlights folder
        
        result = dbCursor.execute(f"""SELECT * FROM Highlight WHERE pk = {pk}""")
        highlights = result.fetchall() # Get the list of highlights from database

        for newHighlight in data:
            update_states.append(updateSingleHighlight(pk, username, newHighlight, highlights)) # Update this highlight

        return data, update_states # Return the highlights data and update states

    except:
        print("Couldn't get the highlights!")
        return data, update_states # There was an error somewhere but return the highlights data and update states anyway

def downloadSingleHighlightStories(username, highlight_id, highlight_title, direct_call = True): # Downloads the stories of a single highlight
    try:
        if direct_call: # If the function is called directly
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
                    highlight_title = new_data['title']
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
        
        number_of_items = downloadStories(pk, username, highlight_id, highlight_title) # Download the stories of the highlight

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

def downloadHighlightsStories(username, direct_call = True): # Downloads the stories of all highlights
    try:
        if direct_call: # If the function is called directly
            updated = updateProfile(username, False) # Update the profile
            if not updated:
                print("Couldn't update the profile!")
        
        result = dbCursor.execute(f"""SELECT pk, is_private FROM Profile WHERE username = '{username}'""")
        pk, is_private = result.fetchone() # Get the pk and is_private of the profile

        if is_private == 1: # If the account is private
            print("This account is private!")
            return
        
        data, update_states = updateHighlights(pk, username) # Update the highlights

        if len(update_states) == 0: # Couldn't update any highlight
            print("Couldn't update the highlights!")
            return
        
        for i in range(len(update_states)):
            if update_states[i]: # If the highlight was updated
                highlight_id = data[i]['id']
                highlight_id = int(highlight_id[highlight_id.index(":") + 1:]) # Get the highlight_id
                
                print(f"Downloading {data[i]['title']}...") # Show the title of the highlight

                downloadSingleHighlightStories(username, highlight_id, data[i]['title'], False) # Download the stories of the highlight

    except:
        print("There was an error!")
        return # There was an error somewhere

connection, dbCursor = initialize() # Initialize the program

if connection is None: # If there was an error in initializing
    print("Couldn't initialize the program!")
    exit() # Exit the program