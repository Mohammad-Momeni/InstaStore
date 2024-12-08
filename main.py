import sqlite3
from PIL import Image, ImageDraw, ImageFilter
from cv2 import VideoCapture, cvtColor, COLOR_BGR2RGB
import os
import shutil
import glob
from time import sleep, time
from mimetypes import guess_extension, guess_type
from curl_cffi import requests
import zendriver as zd
from bs4 import BeautifulSoup
from urllib.parse import unquote
import json

INVALID_CHARACTERS = ['/', '\\', ':', '*', '?', '"', '<', '>', '|'] # Invalid characters for file names

path = os.path.dirname(os.path.abspath(__file__)) + "/storage" # Base path

HEADERS = { # Headers for session
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
}

profile_data = None # Global variable for profile data
stealthgram_tokens = None # Global variable for stealthgram tokens

def initialize():
    '''
    Initializes the basic stuff for the program

    Returns:
        connection (sqlite3.Connection): The connection to the database
        dbCursor (sqlite3.Cursor): The cursor for the database
    '''

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

def makeTables(dbCursor):
    '''
    Creates the tables for the database

    Parameters:
        dbCursor (sqlite3.Cursor): The cursor for the database
    '''

    dbCursor.execute("""CREATE TABLE Profile(pk PRIMARY KEY, username, full_name,
                     page_name, biography, is_private, public_email, media_count,
                     follower_count, following_count, profile_id, last_post_code, last_tagged_post_code)""")
    
    dbCursor.execute("""CREATE TABLE Post(pk, post_code, is_tag, number_of_items, caption, timestamp,
                     PRIMARY KEY(pk, post_code, is_tag), FOREIGN KEY(pk) REFERENCES Profile(pk))""")

    dbCursor.execute("""CREATE TABLE Highlight(highlight_id PRIMARY KEY, pk, title,
                     number_of_items, FOREIGN KEY(pk) REFERENCES Profile(pk))""")
    
    dbCursor.execute("""CREATE TABLE Story(pk, story_pk, highlight_id, timestamp,
                     PRIMARY KEY(pk, story_pk, highlight_id), FOREIGN KEY(pk) REFERENCES Profile(pk),
                     FOREIGN KEY(highlight_id) REFERENCES Highlight(highlight_id))""")
    
    dbCursor.execute("""CREATE TABLE ProfileHistory(pk, profile_id,
                     PRIMARY KEY(pk, profile_id), FOREIGN KEY(pk) REFERENCES Profile(pk))""")
    
    dbCursor.execute("""CREATE TABLE CoverHistory(highlight_id, cover_id, PRIMARY KEY(highlight_id, cover_id),
                     FOREIGN KEY(highlight_id) REFERENCES Highlight(highlight_id))""")

def circleCrop(image):
    '''
    Crops the image to a circle

    Parameters:
        image (PIL.Image): The image to crop
    '''

    blur_radius = 2 # Radius of blurring the edges of the circle thumbnail
    offset = blur_radius * 2

    mask = Image.new("L", image.size, 0) # Creating a mask for the image

    draw = ImageDraw.Draw(mask)
    draw.ellipse((offset, offset, image.size[0] - offset, image.size[1] - offset), fill=255) # Drawing the circle on the mask

    mask = mask.filter(ImageFilter.GaussianBlur(blur_radius)) # Blurring the edges of the circle

    image.putalpha(mask) # Applying the mask to the image
    
def makeThumbnail(address, size, is_video = False, circle = False):
    '''
    Makes a thumbnail for the given file and saves it

    Parameters:
        address (str): The address of the file
        size (int): The size of the thumbnail
        is_video (bool): Is the media a video
        circle (bool): Should the thumbnail be a circle
    
    Returns:
        result (bool): If the thumbnail is made successfully or not
    '''

    try:
        file = glob.glob(path + address + ".*")
        if len(file) != 1:
            return False # Couldn't find the image
        file = file[0]

        if is_video: # If the media is video
            vidcap = VideoCapture(file) # Get the video
            success, image = vidcap.read() # Read the first frame

            if not success: # Couldn't read the frame
                return False # Couldn't make the thumbnail
            
            image = cvtColor(image, COLOR_BGR2RGB) # Convert the image to RGB format
            image = Image.fromarray(image) # Convert the image to PIL format
        
        else:
            image = Image.open(file) # Open the image

        if image.height != image.width: # If the image isn't square
            square_size = min(image.height, image.width) # Get the minimum size

            height_offset = (image.height - square_size) // 2 # Get the offset for height
            width_offset = (image.width - square_size) // 2 # Get the offset for width

            image = image.crop((width_offset, height_offset, width_offset + square_size, height_offset + square_size)) # Crop the image to make it square

        resized_image = image.resize((size, size)) # Resize the image to the thumbnail size

        if circle: # If the thumbnail should be a circle
            circleCrop(resized_image) # Cropping the thumbnail to a circle

        file = file.rsplit('/', 1) # Split the path to get the filename
        filename = file[1].replace("_temp", "") # Remove the "_temp" (if any) from the filename
        file = file[0] + "/" + filename # Get the new path for the thumbnail

        resized_image.save(file[:file.rindex('.')] + "_thumbnail.png") # Saving thumbnail at the same path
        
        return True # Thumbnail made successfully
    
    except:
        return False # Couldn't make the thumbnail

def guessType(file):
    '''
    Guesses the type of the file

    Parameters:
        file (str): The file to guess the type of
    
    Returns:
        mimestart (str): The type of the file
    '''

    mimestart = guess_type(path + file)[0] # Guessing the type of the file

    if mimestart != None:
        mimestart = mimestart.split('/')[0]

        if mimestart in ['image', 'video']:
            return mimestart
        
    return 'None' # Couldn't guess or it wasn't image or video

def MakeFilenameFriendly(text):
    '''
    Makes the text filename friendly

    Parameters:
        text (str): The text to make filename friendly
    
    Returns:
        text (str): The filename friendly text
    '''

    for char in INVALID_CHARACTERS:
        text = text.replace(char, ' ' + str(ord(char)) + ' ') # Replace the invalid characters with their ascii values
    
    return text # Return the filename friendly text

def sendRequest(url, payload=None, headers=None, retries=3, timeout=60):
    '''
    Sends a request to the url and returns the response

    Parameters:
        url (str): The url to send the request
        payload (str): The payload for the request
        headers (dict): The headers for the request
        retries (int): The number of retries for the request
        timeout (int): The timeout for the request
    
    Returns:
        response (requests.Response): The response of the request
    '''

    try:
        response = requests.request("POST", url, data=payload, headers=headers if headers is not None else HEADERS, timeout=timeout) # Send the request
        
        if response.status_code == 200:
            return response # Return the response
        
        elif (response.status_code) == 429 and (retries > 0): # Too many requests
            sleep(30) # Sleep for 30 seconds

            return sendRequest(url, payload, headers, retries - 1) # Try again
        
        elif (response.status_code) == 500: # Internal server error
            if ('stealthgram' in url) and ('EXPIRED' in response.text): # If the tokens are expired
                if not zd.loop().run_until_complete(getStealthgramTokens()): # Get new tokens
                    return None # Couldn't get new tokens
                
                # Set the headers for the request
                headers = {
                    'Cookie': f"access-token={stealthgram_tokens['access-token']}; refresh-token={stealthgram_tokens['refresh-token']};",
                }
                headers.update(HEADERS) # Add the default headers to the request

                return sendRequest(url, payload, headers, retries - 1) # Try again with the new tokens
        
        else:
            return None # Couldn't get the data
    
    except:
        return None # Couldn't get the data

def downloadLink(link, address):
    '''
    Downloads the link and saves it to the address

    Parameters:
        link (str): The link to download
        address (str): The address to save the file
    
    Returns:
        result (bool): If the link is downloaded successfully or not
    '''

    # TODO: Needs change for GUI implementation and multithreading
    try:
        media = requests.get(link, headers=HEADERS, timeout=60, allow_redirects=True) # Get the media from the link

        extension = guess_extension(media.headers['content-type'].partition(';')[0].strip()) # Find the extension from the headers
        if extension is None: # If couldn't find from headers then find from the link
            extension = link[:link.index('?')]
            extension = extension[extension.rindex('.'):]
        
        if extension in [None, '', '.', '.txt', '.html']: # If couldn't find the extension or it's a text or html file (Probably an error)
            return False # Couldn't download the link
        
        open(path + address + extension, 'wb').write(media.content) # saving the file
        return True
    
    except:
        return False # Couldn't download the link

def tryDownloading(link, address, retries = 3):
    '''
    Tries to download the link for retries times

    Parameters:
        link (str): The link to download
        address (str): The address to save the file
        retries (int): The number of retries for the download
    
    Returns:
        result (bool): If the link is downloaded successfully or not
    '''

    isDownloaded = downloadLink(link, address) # Try downloading the link

    if not isDownloaded: # If couldn't download the link, Try 5 more times
        for i in range(retries):
            isDownloaded = downloadLink(link, address) # Try downloading the link

            if isDownloaded: # If downloaded the link
                return True

        if not isDownloaded:
            return False # Couldn't download the link
        
    return True

def listProfiles():
    '''
    Lists the profiles in the database
    '''

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

def moveProfileHistory(username, profile_id):
    '''
    Moves the past profile files (if any) to History folder

    Parameters:
        username (str): The username of the profile
        profile_id (int): The id of the profile
    
    Returns:
        result (bool): If the profile is moved to history successfully or not
    '''

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

async def response_handler(evt: zd.cdp.network.ResponseReceived):
    '''
    Handles the response event for the profile data

    Parameters:
        evt (zd.cdp.network.ResponseReceived): The event object
    '''

    # Check if the event resource type is XHR
    if evt.type_ is zd.cdp.network.ResourceType.XHR:
        # Check if the event url contains 'userInfo' (this is the request that contains the user profile data)
        if 'userInfo' in evt.response.url:
            # get the response body and store it in the global variable
            global profile_data
            profile_data = zd.cdp.network.get_response_body(evt.request_id)

async def ProfileDataAPI(username):
    '''
    Calls the API to get the profile data

    Parameters:
        username (str): The username of the user
    
    Returns:
        data (str): The profile data of the user
    '''

    try:
        # Create a new browser instance in headless mode
        browser = await zd.start(browser_args=["--headless=new", '--disable-gpu'])

        # Create a new page instance
        page = await browser.get('https://anonyig.com/en/')

        # Add a handler for the ResponseReceived event
        page.add_handler(zd.cdp.network.ResponseReceived, response_handler)

        # Wait for the search bar to load
        await page.wait_for('input[type=text]')

        sleep(3) # Wait for 3 seconds

        # Find the search bar
        username_input = await page.select('input[type=text]')

        # Enter the username in the search bar
        await username_input.send_keys(username)

        # Find the search button
        search_button = await page.select('button[class=search-form__button]')

        # Click the search button
        await search_button.click()

        # Wait for the user profile data to load
        await page.wait_for('span[class=user-info__username-text]', timeout=60)

        # Check if the request has been captured
        global profile_data
        if profile_data:
            # Get the profile data
            data = await page.send(cdp_obj=profile_data)
        
        else: # The request has not been captured
            data = None
        
        # Close the page
        await page.close()

        # Stop the browser
        await browser.stop()

        return data # Return the result
    
    except:
        # Close the page
        await page.close()

        # Stop the browser
        await browser.stop()

        return None # There was an error

def getProfileData(username):
    '''
    Gets the profile's data

    Parameters:
        username (str): The username of the profile
    
    Returns:
        profile (dict): The profile's data
    '''

    try:
        # Empty the global variable
        global profile_data
        profile_data = None

        response = zd.loop().run_until_complete(ProfileDataAPI(username)) # Get the profile's data

        if response is None:
            return None # Couldn't get the data
        
        data = json.loads(response[0]) # Parse the data to json
        data = data['result'][0]['user']

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

        return profile # Return profile's data

    except:
        return None # Couldn't get the data

def addProfile(username):
    '''
    Adds a profile to the database

    Parameters:
        username (str): The username of the profile
    
    Returns:
        result (bool): If the profile is added successfully or not
    '''

    try:
        result = dbCursor.execute(f"""SELECT * FROM Profile WHERE username = \"{username}\"""")
        doesExist = result.fetchall() # Get the username information

        if len(doesExist) != 0:
            print("This account is already added!")
            return # Profile already exist, don't need to continue
        
        data = getProfileData(username) # Get the profile's data
        if data is None:
            print("There was an error!")
            return # Couldn't get the data
        
        if not os.path.exists(path + f"/{data['username']}"): # Make the profile folder
            os.mkdir(path + f"/{data['username']}")
        
        if not os.path.exists(path + f"/{data['username']}/Profiles"): # Make the Profiles folder
            os.mkdir(path + f"/{data['username']}/Profiles")
        
        # Else if Profiles folder exist then move the past profile files (if any) to History folder
        elif not moveProfileHistory(data['username'], int(time())):
            print("Couldn't Move the past profile to history!")
            return
    
        isDownloaded = tryDownloading(data['original_profile_pic_link'], data['original_profile_pic']) # Try downloading the profile picture

        if not isDownloaded: # Couldn't download the profile picture
            print("There was an error!")
            return
    
    except:
        print("There was an error!")
        return # Couldn't add the profile
    
    try:
        if not makeThumbnail(data['original_profile_pic'], 128, circle=True): # Try Making a thumbnail for the profile picture
            print("There was an error!")
            return # Couldn't make the thumbnail

        instruction = f"""INSERT INTO Profile VALUES({data['pk']}, \"{data['username']}\", \"{data['full_name']}\","""

        if data['page_name'] is None:
            instruction += "NULL"
        else:
            instruction += f"""\"{data['page_name']}\""""
        
        if data['biography'] == '':
            instruction += f", NULL"
            data['biography'] = None
        else:
            instruction += f""", \"{data['biography']}\""""

        instruction += f""", {data['is_private']},"""

        if data['public_email'] is None:
            instruction += "NULL"
        else:
            instruction += f"""\"{data['public_email']}\""""

        instruction += f""", {data['media_count']}, {data['follower_count']},
                        {data['following_count']}, {data['profile_id']}, NULL, NULL)"""

        dbCursor.execute(instruction) # Add the profile to the database
        dbCursor.execute(f"""INSERT INTO Highlight VALUES({data['pk']}, {data['pk']},
                         "Stories", 0)""") # Add a default highlight for the stories (highlight_id = pk)
        connection.commit() # Commit the changes
        
        if not data['is_private']:
            updateHighlights(data['pk'], data['username']) # If the account isn't private then update it's highlights

        listProfiles() # Update the screen

    except:
        try:
            files = glob.glob(path + f"/{data['username']}/Profiles/Profile*") # Get the profile files

            for file in files:
                os.remove(file) # Remove the profile files
        
        except:
            pass # Couldn't remove the profile files

        connection.rollback() # Rollback the changes
        print("There was an error!") # Couldn't add the profile

def updateProfile(username, withHighlights = True):
    '''
    Updates the profile

    Parameters:
        username (str): The username of the profile
        withHighlights (bool): Should the highlights be updated or not
    
    Returns:
        result (bool): If the profile is updated successfully or not
    '''

    try:
        result = dbCursor.execute(f"""SELECT pk, profile_id FROM Profile WHERE username = \"{username}\"""")
        user_data = result.fetchone() # Get current information of user

        new_data = getProfileData(username) # Get new information of user
        if new_data is None:
            print("Couldn't update profile")
            return False
        
        # Check if profile picture has changed and the last profile isn't default icon
        profile_changed = (user_data[1] != new_data['profile_id']) and (user_data[0] != user_data[1])
        
        if not os.path.exists(path + f"/{username}/Profiles"): # Make the Profiles folder
            os.mkdir(path + f"/{username}/Profiles")
        
        elif profile_changed: # Profile picture has changed
            if not moveProfileHistory(username, user_data[1]): # Move the past profile to history
                print("Couldn't update profile")
                return False
        
        isDownloaded = tryDownloading(new_data['original_profile_pic_link'], new_data['original_profile_pic']) # Try downloading the profile picture

        if not isDownloaded: # Couldn't download the profile picture
            print("Couldn't update profile")
            return False
    
    except:
        print("Couldn't update profile")
        return False # Couldn't update the profile
    
    try:
        if not makeThumbnail(new_data['original_profile_pic'], 128, circle=True): # Try Making a thumbnail for the profile picture
            print("Couldn't update profile")
            return False
        
        instruction = f"""UPDATE Profile SET full_name = \"{new_data['full_name']}\", page_name = """

        if new_data['page_name'] is None:
            instruction += "NULL"
        else:
            instruction += f"""\"{new_data['page_name']}\""""
        
        instruction += ", biography = "
        
        if new_data['biography'] == '':
            instruction += f"NULL"
            new_data['biography'] = None
        else:
            instruction += f"""\"{new_data['biography']}\""""

        instruction += f""", is_private = {new_data['is_private']}, public_email = """

        if new_data['public_email'] is None:
            instruction += "NULL"
        else:
            instruction += f"""\"{new_data['public_email']}\""""

        instruction += f""", media_count = {new_data['media_count']}, follower_count = {new_data['follower_count']},
                        following_count = {new_data['following_count']}, profile_id = {new_data['profile_id']}
                        WHERE pk = {new_data['pk']}"""
        
        dbCursor.execute(instruction) # Update profile's information in database

        if profile_changed: # Profile picture has changed
            dbCursor.execute(f"""INSERT INTO ProfileHistory VALUES({new_data['pk']},
                             {user_data[1]})""") # Add the past profile to history
        
        connection.commit() # Commit the changes

        if withHighlights and (not new_data['is_private']):
            updateHighlights(new_data['pk'], new_data['username']) # If the account isn't private then update it's highlights

        listProfiles() # Update the screen

        return True # Profile updated successfully
        
    except:
        if profile_changed: # Profile picture has changed
            try:
                files = glob.glob(path + f"/{new_data['username']}/Profiles/Profile*") # Get the profile files

                for file in files:
                    os.remove(file) # Remove the profile files
            
            except:
                pass # Couldn't remove the profile files

        connection.rollback() # Rollback the changes
        print("Couldn't update profile")
        return False # Threre was an error somewhere

def checkDuplicateStories(pk, username, story_pk, highlight_id, highlight_title, stories):
    '''
    Checks if the story is already downloaded

    Parameters:
        pk (int): The profile's pk
        username (str): The username of the profile
        story_pk (int): The story's pk
        highlight_id (int): The highlight's id
        highlight_title (str): The highlight's title
        stories (list): The list of stories
    
    Returns:
        result (bool): If the story already exists and downloaded or not
    '''

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
                            connection.commit() # Commit the changes
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
                                connection.commit() # Commit the changes
                                return True
                            
                    except:
                        connection.rollback() # Rollback the changes
                        return False # Something went wrong but we know it's not from the same highlight

                break # One story with same story_pk is enough
        
        return False # Couldn't find the story
    
    except:
        connection.rollback() # Rollback the changes
        return None # Something went wrong

async def getStealthgramTokens():
    '''
    Gets the stealthgram tokens

    Returns:
        result (bool): If the tokens are updated successfully or not
    '''

    try:
        # Create a new browser instance in headless mode
        browser = await zd.start(browser_args=["--headless=new", '--disable-gpu'])

        # Create a new page instance
        page = await browser.get('https://stealthgram.com/profile/test')

        sleep(3) # Wait for the data to load

        # Get the cookies
        cookies = await page.send(cdp_obj=zd.cdp.network.get_cookies(urls=[f'https://stealthgram.com/profile/test']))

        # Get the tokens from the cookies
        global stealthgram_tokens
        stealthgram_tokens = {}

        for cookie in cookies:
            if cookie.name == 'access-token':
                stealthgram_tokens['access-token'] = cookie.value
            
            elif cookie.name == 'refresh-token':
                stealthgram_tokens['refresh-token'] = cookie.value
        
        # Close the page
        await page.close()

        # Stop the browser
        await browser.stop()

        return True # Tokens updated successfully
    
    except:
        # Close the page
        await page.close()

        # Stop the browser
        await browser.stop()

        return False # Couldn't update the tokens

def updateStealthgramTokens(headers):
    '''
    Updates the stealthgram tokens

    Parameters:
        headers (Headers): The headers of the request
    
    Returns:
        result (bool): If the tokens are updated successfully or not
    '''

    try:
        set_cookies = headers.get('set-cookie').split(' ') # Get the set-cookie's from the headers
        
        global stealthgram_tokens
        for cookie in set_cookies:
            if 'access-token' in cookie:
                stealthgram_tokens['access-token'] = cookie[cookie.index('=') + 1:cookie.index(';')]
            
            elif 'refresh-token' in cookie:
                stealthgram_tokens['refresh-token'] = cookie[cookie.index('=') + 1:cookie.index(';')]
    
        return True # Tokens updated successfully
    
    except:
        return False # Couldn't update the tokens

def callStealthgramAPI(pk, highlight_id, is_highlight=False):
    '''
    Calls the stealthgram API to get the data

    Parameters:
        pk (int): The profile's pk
        highlight_id (int): The highlight's id
        is_highlight (bool): Is the data for highlight or not
    
    Returns:
        response (requests.Response): The response of the request
    '''
    
    try:
        # Base API link
        link = "https://stealthgram.com/api/apiData"

        # Set the payload for the request
        if is_highlight: # If the data is for highlight
            payload = json.dumps({
                "body": {
                    "id": str(pk),
                },
                "url": "user/get_highlights"
            })
        
        else:
            if pk != highlight_id: # highlight_id == pk is for stories
                payload = json.dumps({
                    "body": {
                        "ids": [
                            str(highlight_id)
                        ],
                    },
                    "url": "highlight/get_stories"
                })

            else:
                payload = json.dumps({
                    "body": {
                        "ids": [
                            highlight_id
                        ],
                    },
                    "url": "user/get_stories"
                })
        
        # Check if stealthgram tokens are available
        global stealthgram_tokens
        if stealthgram_tokens is None:
            if not zd.loop().run_until_complete(getStealthgramTokens()):
                return None # Couldn't update the tokens
        
        # Set the headers for the request
        headers = {
            'Cookie': f"access-token={stealthgram_tokens['access-token']}; refresh-token={stealthgram_tokens['refresh-token']};",
        }
        headers.update(HEADERS) # Add the default headers to the request

        response = sendRequest(link, payload, headers) # Get the data

        updateStealthgramTokens(response.headers) # Update the stealthgram tokens

        return response # Return the response
    
    except:
        return None # There was an error
    

def getStoriesData(pk, highlight_id):
    '''
    Gets the stories (or highlights) data of the profile

    Parameters:
        pk (int): The profile's pk
        highlight_id (int): The highlight's id
    
    Returns:
        data (list): The stories data
    '''

    try:
        response = callStealthgramAPI(pk, highlight_id) # Get the stories data

        if response is None:
            return None # Couldn't get the data

        data = json.loads(response.text) # Parse the data to json

        # Set the label for getting the stories from the response
        label = ('highlight:' if pk != highlight_id else '') + str(highlight_id)

        # If there is currently no story or highlight
        if label not in data['response']['body']['reels'].keys():
            return [] # Return an empty list
        
        else: # If there is a story or highlight
            data = data['response']['body']['reels'][label]['items']

        return data # Return the stories data
    
    except:
        return None # Couldn't get the stories data

def getSingleStory(pk, username, new_story, highlight_id, highlight_title, stories):
    '''
    Gets a single story for download

    Parameters:
        pk (int): The profile's pk
        username (str): The username of the profile
        new_story (dict): The new story data
        highlight_id (int): The highlight's id
        highlight_title (str): The highlight's title
        stories (list): The list of stories
    
    Returns:
        story (tuple): The story information
    '''

    try:
        story_pk = int(new_story['id'][:new_story['id'].find('_')]) # The story's pk

        downloaded = checkDuplicateStories(pk, username, story_pk, highlight_id, highlight_title, stories) # Check if the story is already downloaded

        if downloaded or (downloaded is None):
            return None # It was (found and copied) or (couldn't check and it may be duplicate) so skip this one

        timestamp = new_story['taken_at'] # The timestamp of the story

        media_link = None # The media link of the story
        is_video = False # Is the story is video

        if 'video_versions' in new_story.keys(): # If the story is video
            media_link = new_story['video_versions'][0]['url']
            is_video = True

        if media_link is None: # If story isn't video then get the best picture
            media_link = new_story['image_versions2']['candidates'][0]['url']

        # Set the saving address according to being a story or highlight
        if pk != highlight_id: # highlight_id == pk is for stories
            media_address = f"/{username}/Highlights/{MakeFilenameFriendly(highlight_title)}_{highlight_id}/{story_pk}"

        else:
            media_address = f"/{username}/Stories/{story_pk}"
        
        return (pk, story_pk, highlight_id, timestamp, media_link, media_address, is_video) # Return the story information
    
    except:
        return None # Something went wrong

def getStories(pk, username, highlight_id, highlight_title):
    '''
    Gets the stories or highlights of the profile for download

    Parameters:
        pk (int): The profile's pk
        username (str): The username of the profile
        highlight_id (int): The highlight's id
        highlight_title (str): The highlight's title
    
    Returns:
        newStories (list): The list of new stories
        number_of_items (int): The number of items
    '''

    try:
        data = getStoriesData(pk, highlight_id) # Get the stories data

        if data is None:
            return None, 0 # Couldn't get the stories data

        number_of_items = len(data) # Number of items in the stories or highlights

        if number_of_items == 0:
            return [], 0 # Return an empty list if there is no story
        
        result = dbCursor.execute(f"""SELECT * FROM Story WHERE pk = {pk}""")
        stories = result.fetchall() # Get the list of already downloaded stories from database

        newStories = [] # List of new stories that need downloading
        
        for new_story in data:
            new_story_data = getSingleStory(pk, username, new_story, highlight_id, highlight_title, stories) # Get the story information

            if new_story_data is None:
                continue # Couldn't get the story information so skip this one

            newStories.append(new_story_data) # Add the story information to the list of new stories
        
        return newStories, number_of_items # Return the list of new stories and the number of items
            
    except:
        return None, number_of_items # Something went wrong

def downloadStories(pk, username, highlight_id, highlight_title):
    '''
    Downloads the stories or highlights of the profile
    
    Parameters:
        pk (int): The profile's pk
        username (str): The username of the profile
        highlight_id (int): The highlight's id
        highlight_title (str): The highlight's title
    
    Returns:
        number_of_items (int): The number of items
    '''

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

            if not isDownloaded: # Couldn't download the media
                print("Couldn't download story!")
                continue

            if not makeThumbnail(story[5], 320, is_video=story[6]): # Try making a thumbnail for the media
                print("Couldn't download story!")
                continue
            
            dbCursor.execute(f"""INSERT INTO Story VALUES({story[0]}, {story[1]},
                             {story[2]}, {story[3]})""") # Add the story to the database
            connection.commit() # Commit the changes

        except:
            connection.rollback() # Rollback the changes
            print("There was an error!")
            continue # Couldn't download, skip and try the next one
    
    return number_of_items # Return the number of items

def addCoverHistory(username, highlight_id, new_cover_link):
    '''
    Checks the highlight cover and if it has changed then add it to the database

    Parameters:
        username (str): The username of the profile
        highlight_id (int): The highlight's id
        new_cover_link (str): The new cover link
    
    Returns:
        status (str): The status of the cover
    '''

    try:
        folder = glob.glob(path + f"/{username}/Highlights/*_{highlight_id}") # Check if the highlight folder already exists

        if len(folder) == 0: # If the folder doesn't exist
            return "No File" # There is no folder so there is nothing to do
        
        cover_file = glob.glob(folder[0] + "/Cover.*") # Check if the cover exists

        if len(cover_file) == 0: # If the cover doesn't exist
            return "No File" # There is no cover so there is nothing to do
        
        old_cover = open(cover_file[0], 'rb').read() # Get the old cover

        new_cover = requests.get(new_cover_link, allow_redirects=True, timeout=60) # Get the new cover

        if old_cover == new_cover.content: # If the cover hasn't changed
            return "Same" # The cover is the same
        
        if not os.path.exists(folder[0] + "/History"): # Make the History folder
            os.mkdir(folder[0] + "/History")
        
        new_name = int(time()) # Get the new name for the cover

        shutil.move(cover_file[0], folder[0] + f"/History/{new_name}"
                    + cover_file[0][cover_file[0].rindex('.'):]) # Move the old cover to History folder
        
        if os.path.exists(folder[0] + "/Cover_thumbnail.png"): # If the thumbnail exists
            shutil.move(folder[0] + "/Cover_thumbnail.png", folder[0] +
                        f"/History/{new_name}_thumbnail.png") # Move the old thumbnail to History folder
        
        try:
            dbCursor.execute(f"""INSERT INTO CoverHistory VALUES({highlight_id}, {new_name})""") # Add the cover to the database
            connection.commit() # Commit the changes
        
        except:
            connection.rollback() # Rollback the changes
        
        return "Changed" # The cover has changed

    except:
        return None # Something went wrong

def getHighlightsData(pk):
    '''
    Gets the highlights data of the profile

    Parameters:
        pk (int): The profile's pk
    
    Returns:
        data (list): The highlights data
    '''

    try:
        response = callStealthgramAPI(pk, None, True) # Get the highlights data

        if response is None: # Couldn't get the highlights data
            return None
        
        data = json.loads(response.text)
        data = data['response']['body']['data']['user']['edge_highlight_reels']['edges']

        return data # Return the highlights data
    
    except:
        return None # Couldn't get the highlights data

def updateSingleHighlight(pk, username, newHighlight, highlights):
    '''
    Updates a single highlight

    Parameters:
        pk (int): The profile's pk
        username (str): The username of the profile
        newHighlight (dict): The new highlight data
        highlights (list): The list of highlights
    
    Returns:
        result (bool): If the highlight is updated successfully or not
    '''

    try:
        highlight_id = int(newHighlight['id'])

        title = newHighlight['title']
        folder_name = MakeFilenameFriendly(title) # Make the title filename friendly
        cover_link = newHighlight['cover_media_cropped_thumbnail']['url']

        folder = glob.glob(path + f"/{username}/Highlights/*_{highlight_id}") # Check if the highlight folder already exists

        for i in range(len(highlights)):
            if highlights[i][0] == highlight_id: # If highlight already exists

                if (highlights[i][2] == title): # If title hasn't changed
                    if (len(folder) == 0): # And folder doesn't exist
                        os.mkdir(path + f"/{username}/Highlights/{folder_name}_{highlight_id}")

                else:

                    if len(folder) > 0: # If folder exists then rename it
                        for i in folder[1:]:
                            shutil.copytree(i, folder[0], dirs_exist_ok=True) # Copy the files from the other folders to the first one
                            shutil.rmtree(i) # Remove the other folders
                        
                        os.rename(folder[0], path + f"/{username}/Highlights/{folder_name}_{highlight_id}") # Rename the folder
                        
                    else:
                        os.mkdir(path + f"/{username}/Highlights/{folder_name}_{highlight_id}")
                    
                    try:
                        dbCursor.execute(f"""UPDATE Highlight SET title = \"{title}\"
                                        WHERE highlight_id = {highlight_id}""") # Update the title
                        connection.commit() # Commit the changes
                    
                    except:
                        connection.rollback() # Rollback the changes
                        return True # Couldn't Update the database but the folder is updated at least
                
                cover_status = addCoverHistory(username, highlight_id, cover_link) # Check the highlight cover and if it has changed then add it to the database
                if cover_status is None:
                    return True # Couldn't check the cover but the highlight is updated at least

                if cover_status != "Same": # If the cover file doesn't exist or it has changed
                    isDownloaded = tryDownloading(cover_link, f"/{username}/Highlights/{folder_name}_{highlight_id}/Cover") # Try downloading highlight's cover

                    if isDownloaded: # If the cover is downloaded
                        makeThumbnail(f"/{username}/Highlights/{folder_name}_{highlight_id}/Cover", 64, circle=True) # Make thumbnail for cover

                del(highlights[i])
                return True # Highlight was found and updated
        
        # If this highlight is new
        if len(folder) == 0:
            os.mkdir(path + f"/{username}/Highlights/{folder_name}_{highlight_id}")

        else:
            for i in folder[1:]:
                shutil.copytree(i, folder[0], dirs_exist_ok=True) # Copy the files from the other folders to the first one
                shutil.rmtree(i) # Remove the other folders
            
            os.rename(folder[0], path + f"/{username}/Highlights/{folder_name}_{highlight_id}")
        
        try:
            dbCursor.execute(f"""INSERT INTO Highlight VALUES({highlight_id}, {pk}, \"{title}\", 0)""") # Add it to database
            connection.commit() # Commit the changes
        
        except:
            connection.rollback() # Rollback the changes
            return False # Couldn't add the highlight to the database

        cover_status = addCoverHistory(username, highlight_id, cover_link) # Check the highlight cover and if it has changed then add it to the database
        if cover_status is None:
            return True # Couldn't check the cover but the highlight is added at least

        if cover_status != "Same": # If the cover file doesn't exist or it has changed
            isDownloaded = tryDownloading(cover_link, f"/{username}/Highlights/{folder_name}_{highlight_id}/Cover") # Try downloading highlight's cover

            if isDownloaded: # If the cover is downloaded
                makeThumbnail(f"/{username}/Highlights/{folder_name}_{highlight_id}/Cover", 64, circle=True) # Make thumbnail for the cover
        
        return True # Highlight was added

    except:
        return False # There was an error somewhere

def updateHighlights(pk, username):
    '''
    Updates the highlights of the profile

    Parameters:
        pk (int): The profile's pk
        username (str): The username of the profile
    
    Returns:
        data (list): The highlights data
        update_states (list): The list of update states
    '''

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
            update_states.append(updateSingleHighlight(pk, username, newHighlight['node'], highlights)) # Update this highlight

        return data, update_states # Return the highlights data and update states

    except:
        print("Couldn't get the highlights!")
        return data, update_states # There was an error somewhere but return the highlights data and update states anyway

def downloadSingleHighlightStories(username, highlight_id, highlight_title, direct_call = True):
    '''
    Downloads the stories of a single highlight

    Parameters:
        username (str): The username of the profile
        highlight_id (int): The highlight's id
        highlight_title (str): The highlight's title
        direct_call (bool): If the function is called directly or not
    '''

    try:
        if direct_call: # If the function is called directly
            updated = updateProfile(username, False) # Update the profile

            if not updated:
                print("Couldn't update the profile!")
        
        result = dbCursor.execute(f"""SELECT pk, is_private FROM Profile WHERE username = \"{username}\"""")
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
                highlight = highlight['node']

                if highlight['id'] == highlight_id: # If the highlight_id is found in the data
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
                
                result = dbCursor.execute(f"""SELECT COUNT(*) FROM Story WHERE pk = {pk} AND highlight_id = {highlight_id}""")
                number_of_downloaded = result.fetchone()[0] # Get the number of downloaded stories

                new_max = max(number_of_items, number_of_downloaded) # Get the new maximum number of items

                if new_max > old_number_of_items: # If the new maximum is greater than the old maximum
                    dbCursor.execute(f"""UPDATE Highlight SET number_of_items = {new_max}
                                    WHERE highlight_id = {highlight_id}""") # Update the number of items in the database
                    connection.commit() # Commit the changes

        except: # Couldn't update the number of items
            pass

    except:
        print("Couldn't download the highlight!")
        return # There was an error somewhere

def downloadHighlightsStories(username, direct_call = True):
    '''
    Downloads the stories of all highlights

    Parameters:
        username (str): The username of the profile
        direct_call (bool): If the function is called directly or not
    '''

    try:
        if direct_call: # If the function is called directly
            updated = updateProfile(username, False) # Update the profile

            if not updated:
                print("Couldn't update the profile!")
        
        result = dbCursor.execute(f"""SELECT pk, is_private FROM Profile WHERE username = \"{username}\"""")
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
                highlight_id = int(data[i]['node']['id']) # Get the highlight_id
                
                print(f"Downloading {data[i]['node']['title']}...") # Show the title of the highlight

                downloadSingleHighlightStories(username, highlight_id, data[i]['node']['title'], False) # Download the stories of the highlight

    except:
        print("There was an error!")
        return # There was an error somewhere

def toGoogleTranslateLink(link): # Converts the link to Google Translate version link
    try:
        if 'www.' in link: # If the link has www.
            link = link[link.index('www.') + 4:] # Remove the www. from the link
        
        else:
            link = link[link.index('//') + 2:] # Remove the https:// from the link

        link = link.split('/', 1) # Split the link to parts

        link[0] = link[0].replace('-', '--') # Replace - with -- in the link
        link[0] = "https://" + link[0].replace('.', '-') + ".translate.goog" # Change the link to Google Translate version

        if not '?' in link[1]: # If there is no ? in the link
            link[1] += '?' # Add ? to the link
        
        else: # If there is ? in the link
            link[1] += '&' # Add & to the link
        
        link[1] += '_x_tr_sl=auto&_x_tr_tl=en&_x_tr_hl=en-US&_x_tr_pto=wapp' # Add the translation options to the link

        link = '/'.join(link) # Join the link parts

        return link # Return the Google Translate version link
    
    except:
        return None # Couldn't convert the link

def callPostCodeAPI(pk, username, is_tag, is_cursor = True, cursor = None): # Calls the API for the (tagged/normal) posts codes of the profile
    try:
        # Get the proper link according to being a post or tagged post and having a cursor or not
        if is_tag: # If the posts are tagged posts
            if is_cursor: # If there is a cursor
                link = f"https://imginn.com/api/tagged?id={pk}&cursor={cursor}" # Call the tagged posts data API with the cursor
            
            else: # If there is no cursor
                link = f"https://imginn.com/tagged/{username}" # Call the tagged posts page link
        
        else:
            if is_cursor: # If there is a cursor
                link = f"https://imginn.com/api/posts/?id={pk}&cursor={cursor}" # Call the posts data API with the cursor
            
            else: # If there is no cursor
                link = f"https://imginn.com/{username}" # Call the posts page link
        
        response = sendRequest(toGoogleTranslateLink(link)) # Get the data

        if response is None:
            return None # Couldn't get the data
        
        if is_cursor: # If there is a cursor
            data = json.loads(response.text) # Parse the data to json

            if ((not is_tag) and (data['code'] != 200)) or ((is_tag) and (len(data.keys()) == 0)): # There is an error
                return None # Couldn't get the data
            
            return data # Return the data
        
        else: # If there is no cursor
            soap = BeautifulSoup(response.text, 'html.parser') # Parse the response using BeautifulSoup to get the data

            return soap # Return the data
    
    except:
        return None # Couldn't get the posts data

def addSinglePost(pk, post_code, is_tag): # Adds a single post to the database
    try:
        result = dbCursor.execute(f"""SELECT * FROM Post WHERE pk = {pk} AND post_code = \"{post_code}\" AND is_tag = {is_tag}""")
        doesExist = result.fetchall() # Try to get the post from the database to check if it's already recorded
        
        if len(doesExist) == 0: # If the post isn't recorded
            try:
                dbCursor.execute(f"""INSERT INTO Post VALUES({pk}, \"{post_code}\", {is_tag}, NULL, NULL, NULL)""") # Add the post to the database
                connection.commit() # Commit the changes
            
            except:
                connection.rollback() # Rollback the changes
                return False # Couldn't add the post to the database
        
        return True # The post is added to the database or it's already recorded
    
    except:
        return False # Couldn't add the post to the database

def addPostsCodes(pk, username, is_tag): # adds the (tagged/normal) posts codes of the profile
    try:
        if is_tag: # If the posts are tagged posts
            instruction = "last_tagged_post_code" # The instruction for the last post
        
        else:
            instruction = "last_post_code" # The instruction for the last post
        
        soap = callPostCodeAPI(pk, username, is_tag, is_cursor=False) # Get the data

        if soap is None: # If there is an error
            return False # Couldn't get the data
    
    except:
        return False # Couldn't get the data
    
    try:
        result = dbCursor.execute(f"""SELECT {instruction} FROM Profile
                                WHERE username = \"{username}\"""") # Get the last post that is checked
        
        last_post = result.fetchone()[0] # Get the last post that is checked

        new_last_post = last_post # The new last post that is checked

        items = soap.find_all(attrs={'class': 'item'}) # Get the items of the posts

        for i in range (len(items)):
            post_code = items[i].find(attrs={'class': 'img'}).find('a').attrs['href'] # Get the post link
            post_code = post_code[post_code.index('p/') + 2:post_code.rindex('/')] # Get the post code

            if not addSinglePost(pk, post_code, is_tag): # Add the post to the database
                new_last_post = post_code # Couldn't add the post to the database
            
            if (is_tag and i == 0) or ((not is_tag) and i == 3): # If it's the first tagged post or the 4th post (the first post that is certainly not pinned)
                new_last_post = post_code # Set the last post that is checked
            
            if (i > 2 or is_tag) and last_post == post_code: # If the post is the last post that is checked
                try:
                    if new_last_post != last_post: # If the last post that is checked has changed
                        dbCursor.execute(f"""UPDATE Profile SET {instruction} = \"{new_last_post}\"
                                        WHERE username = \"{username}\"""") # Update the last post that is checked
                        connection.commit() # Commit the changes
                
                except:
                    connection.rollback() # Rollback the changes

                return True # All the posts are checked
        
        try:
            cursor = soap.find(attrs={'class': 'load-more'})
            cursor = cursor.attrs['data-cursor'] # Get the cursor for the next set of posts
        
        except:
            if new_last_post != last_post: # If the last post that is checked has changed
                dbCursor.execute(f"""UPDATE Profile SET {instruction} = \"{new_last_post}\"
                                WHERE username = \"{username}\"""") # Update the last post that is checked
                connection.commit() # Commit the changes

            return True # All the posts are checked
        
        couldnt_get_all = False # Flag for if couldn't get all the posts data

        while True: # Get the next set of posts until there is no more post
            data = callPostCodeAPI(pk, username, is_tag, is_cursor=True, cursor=cursor) # Get the data

            if data is None: # Couldn't get the data
                couldnt_get_all = True # Couldn't get all the posts data
                break
            
            items = data['items'] # Get the items of the posts
            
            for item in items:
                post_code = item['code'] # Get the post code

                if not addSinglePost(pk, post_code, is_tag): # Add the post to the database
                    new_last_post = post_code # Couldn't add the post to the database
                
                if last_post == post_code: # If the post is the last post that is checked
                    try:
                        if new_last_post != last_post: # If the last post that is checked has changed
                            dbCursor.execute(f"""UPDATE Profile SET {instruction} = \"{new_last_post}\"
                                            WHERE username = \"{username}\"""") # Update the last post that is checked
                            connection.commit() # Commit the changes
                    
                    except:
                        connection.rollback() # Rollback the changes

                    return True # All the posts are checked
            
            if data['hasNext']: # If there is more post
                cursor = data['cursor'] # Get the cursor for the next set of posts
            
            else:
                break # There is no more post
        
        try:
            if (not couldnt_get_all) and (new_last_post != last_post): # If the last post that is checked has changed
                dbCursor.execute(f"""UPDATE Profile SET {instruction} = \"{new_last_post}\"
                                WHERE username = \"{username}\"""") # Update the last post that is checked
                connection.commit() # Commit the changes
        
        except:
            connection.rollback() # Rollback the changes
        
        return True # All the posts are checked
    
    except:
        return False # Couldn't get all the posts data

def callPostPageAPI(post_code): # Calls the API for the post page
    try:
        link = f"https://imginn.com/p/{post_code}" # The link for the post page

        response = sendRequest(toGoogleTranslateLink(link)) # Get the data

        if response is None:
            return None # Couldn't get the data
        
        soap = BeautifulSoup(response.text, 'html.parser') # Parse the response using BeautifulSoup to get the data

        return soap # Return the data
    
    except:
        return None # Couldn't get the data

def getSinglePostData(post_code): # Gets the data of a single post
    try:
        soap = callPostPageAPI(post_code) # Get the data

        if soap is None:
            return None # Couldn't get the post data
        
        data = soap.find(attrs={'class': 'page-post'}) # Find the post data

        try:
            caption = data.find(attrs={'class': 'desc'}).text.strip() # Get the caption of the post
        
        except:
            caption = None # Post doesn't have a caption

        timestamp = int(data.get_attribute_list('data-created')[0]) # Get the timestamp of the post

        links = [] # List of media links

        single_media = False # Flag for if the post has single media

        try:
            swiper = data.find(attrs={'class': 'swiper-wrapper'}) # Get the swiper of the post

            if swiper is not None: # If the post has multiple media
                try:
                    slide = swiper.find_all(attrs={'class': 'swiper-slide'}) # Get the slides of the post

                    for item in slide:
                        item_type = 'img' # The type of the media

                        if item.find('video') is not None: # If the media is video
                            item_type = 'video' # Set the type to video
                        
                        link = item.get_attribute_list('data-src')[0] # Get the media link

                        if 'null.jpg' in link: # If the media link is null
                            link = item.find(item_type).attrs['poster'] # Get the poster link instead
                            item_type = 'img' # Set the type to image

                        if 'imginn' in link: # If the media link is from imginn
                            link = toGoogleTranslateLink(link) # Convert the link to Google Translate version link
                        
                        links.append((link, item_type)) # Add the media link to the list
                
                except:
                    return None # Couldn't get the post data
            
            else: # If the post has single media
                single_media = True # The post has single media
        
        except: # If the post has single media
            single_media = True # The post has single media

        if single_media: # If the post has single media
            download = data.find(attrs={'class': 'downloads'}) # Get the download section of the post

            if download is not None: # If the post has download section
                media = data.find(attrs={'class': 'media-wrap'}) # Get the media of the post

                item_type = 'img' # The type of the media

                if len(media.get_attribute_list('class')) == 2: # If the media is video
                    item_type = 'video' # Set the type to video

                link = download.find('a').attrs['href'] # Get the media link

                if 'u=' in link: # If the media link is from google translation
                    link = link[link.index('u=') + 2:] # Get rid of google translation part of the link

                    link = unquote(link) # Decode the link

                if 'null.jpg' in link: # If the media link is null
                    link = media.find(item_type).attrs['poster'] # Get the poster link instead
                    item_type = 'img' # Set the type to image

                if '&dl' in link: # If the media link is direct download link
                    link = link[:link.index('&dl')] # Get the media link

                if 'imginn' in link: # If the media link is from imginn
                    link = toGoogleTranslateLink(link) # Convert the link to Google Translate version link
                
                links.append((link, item_type)) # Add the media link to the list
        
        return (caption, timestamp, links) # Return the post data
    
    except:
        return None # Couldn't get the post data

def downloadSinglePost(post_code, is_tag, address): # Downloads a single post
    try:
        data = getSinglePostData(post_code) # Get the data

        if data is None: # Couldn't get the data
            return False # Couldn't download the post
        
        caption = data[0] # Get the caption of the post
        timestamp = data[1] # Get the timestamp of the post
        links = data[2] # Get the media links of the post
        
        for i in range(len(links)):
            try:
                isDownloaded = tryDownloading(links[i][0], f"{address}/{post_code}_{i}") # Try downloading the media

                if not isDownloaded: # Couldn't download the media
                    return False # Couldn't download the post
                
                if not makeThumbnail(f"{address}/{post_code}_{i}", 320, is_video=(links[i][1] == 'video')): # Try making a thumbnail for the media
                    return False # Couldn't download the post
            
            except:
                return False # Couldn't download the post
        
        try:
            instruction = f"""UPDATE Post SET number_of_items = {len(links)}, caption =""" # The instruction for updating the post

            if caption is None or caption == "":
                instruction += " NULL," # If the caption is empty

            else:
                instruction += f""" \"{caption}\", """

            instruction += f"""timestamp = {timestamp} WHERE post_code = \"{post_code}\" AND is_tag = {is_tag}"""

            dbCursor.execute(instruction) # Update the post in the database
            connection.commit() # Commit the changes
        
        except:
            connection.rollback() # Rollback the changes
            return False # Couldn't update the post in the database
        
        return True # The post is downloaded
    
    except:
        return False # Couldn't download the post

def downloadPosts(username, is_tag, direct_call = True): # Downloads the (tagged/normal) posts of the profile
    try:
        if direct_call: # If the function is called directly
            updated = updateProfile(username, False) # Update the profile

            if not updated:
                print("Couldn't update the profile!")
        
        result = dbCursor.execute(f"""SELECT pk, is_private FROM Profile WHERE username = \"{username}\"""")
        pk, is_private = result.fetchone() # Get the pk and is_private of the profile

        if is_private == 1: # If the account is private
            print("This account is private!")
            return False # It's not possible to download the posts of a private account

        addPostsCodes(pk, username, is_tag) # Add the (tagged/normal) posts codes of the profile

        result = dbCursor.execute(f"""SELECT post_code FROM Post WHERE pk = {pk} AND
                                  is_tag = {is_tag} AND number_of_items IS NULL""")
        posts = result.fetchall() # Get the list of posts that are not downloaded yet

        if is_tag: # If the posts are tagged posts
            address = f"/{username}/Tagged" # The address for the tagged posts
        
        else:
            address = f"/{username}/Posts" # The address for the normal posts

        if not os.path.exists(path + address):
            os.mkdir(path + address) # Make the folder for the posts
        
        for post in posts:
            try:
                downloadSinglePost(post[0], is_tag, address) # Download the post
            
            except:
                continue # Couldn't download the post, skip and try the next one
        
        return True # Posts are downloaded
    
    except:
        return False # Couldn't download any post

connection, dbCursor = initialize() # Initialize the program

if connection is None: # If there was an error in initializing
    print("Couldn't initialize the program!")
    exit() # Exit the program