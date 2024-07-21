import sqlite3
import os
import requests
import json

path = os.path.dirname(os.path.abspath(__file__)) + "\\storage"

def initialize():
    if not os.path.exists(path):
        os.mkdir(path)
    
    initializeTables = False
    if not os.path.exists(path + "\\data.db"):
        initializeTables = True

    connection = sqlite3.connect(path + "\\data.db")
    dbCursor = connection.cursor()

    dbCursor.execute("PRAGMA foreign_keys = ON")

    if initializeTables:
        makeTables()
    return connection, dbCursor

def makeTables(dbCursor):
    dbCursor.execute("CREATE TABLE Media(name PRIMARY KEY, type)")

    dbCursor.execute("""CREATE TABLE Profile(pk PRIMARY KEY, username, full_name, page_name, biography,
                public_email, media_count, follower_count, following_count, original_profile_pic, small_profile_pic,
                FOREIGN KEY(original_profile_pic) REFERENCES Media(name), FOREIGN KEY(small_profile_pic) REFERENCES Media(name))""")
    
    dbCursor.execute("CREATE TABLE Post(pk, link, caption, timestamp, isTag, PRIMARY KEY(pk, link), FOREIGN KEY(pk) REFERENCES Profile(pk))")

    dbCursor.execute("""CREATE TABLE Highlight(pk, id, title, cover_image, PRIMARY KEY(pk, id),
                FOREIGN KEY(pk) REFERENCES Profile(pk), FOREIGN KEY(cover_image) REFERENCES Media(name))""")
    
    dbCursor.execute("""CREATE TABLE Story(pk, story_pk, highlight_id, timestamp, PRIMARY KEY(pk, story_pk),
                FOREIGN KEY(pk) REFERENCES Profile(pk), FOREIGN KEY(highlight_id) REFERENCES Highlight(id))""")
    
    dbCursor.execute("""CREATE TABLE Content(id, number, media, thumbnail, PRIMARY KEY(id, number),
                FOREIGN KEY(media) REFERENCES Media(name), FOREIGN KEY(thumbnail) REFERENCES Media(name))""")
    
    dbCursor.execute("CREATE TABLE ProfileHistory(pk, number, media, PRIMARY KEY(pk, number), FOREIGN KEY(pk) REFERENCES Profile(pk), FOREIGN KEY(media) REFERENCES Media(name))")

def downloadLink(link, address):
    try:
        media = requests.get(link, allow_redirects=True)
        open(path + address, 'wb').write(media.content)
        return True
    except:
        return False

def listProfiles():
    # Needs change for GUI implementation
    for profile in profiles:
        print(profile[0] + ":\n" + profile[1] + "\n" + profile[2] + "\nPosts: " + str(profile[3]) + "\nFollowers: " + str(profile[4]) + "\nFollowings: " + str(profile[5]))
        print("---------------------------------")

connection, dbCursor = initialize()

result = dbCursor.execute("SELECT username, full_name, biography, media_count, follower_count, following_count, small_profile_pic FROM Profile")
profiles = result.fetchall()