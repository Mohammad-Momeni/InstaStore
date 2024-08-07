from PyQt5 import QtCore, QtGui, QtWidgets
import os

path = os.path.dirname(os.path.abspath(__file__)) # Base path

class Profile_Item(QtWidgets.QWidget): # Profile Item Class
    def __init__ (self, profile_data):
        super(Profile_Item, self).__init__() # Super Class

        self.username = profile_data[0] # Username
        self.biography = profile_data[1] # Biography
        self.posts = profile_data[2] # Posts
        self.followers = profile_data[3] # Followers
        self.followings = profile_data[4] # Followings
        self.is_profile_downloaded = profile_data[5] # Is downloaded or not

        self.__setupUi() # UI initialization

    def __setupUi(self): # Initialize UI
        # Set up of profile layout
        self.profile_layout_widget = QtWidgets.QWidget()
        self.profile_layout_widget.setGeometry(QtCore.QRect(0, 0, 513, 201))
        self.profile_layout_widget.setObjectName("profile_layout_widget")
        self.profile_layout = QtWidgets.QHBoxLayout(self.profile_layout_widget)
        self.profile_layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        self.profile_layout.setContentsMargins(0, 0, 0, 0)
        self.profile_layout.setObjectName("profile_layout")

        #Set up of profile pic
        self.profile_pic = QtWidgets.QLabel(self.profile_layout_widget)
        self.profile_pic.setText("")
        self.profile_pic.setPixmap(QtGui.QPixmap(path + f"/storage/{self.username}/Profiles/Profile_thumbnail.png"))
        self.profile_pic.setAlignment(QtCore.Qt.AlignCenter)
        self.profile_pic.setObjectName("profile_pic")
        self.profile_pic.setFixedSize(128, 199)
        self.profile_layout.addWidget(self.profile_pic)

        # Set up of left layout (username, biography, posts and followers)
        self.left_layout = QtWidgets.QVBoxLayout()
        self.left_layout.setObjectName("left_layout")

        # Set up of username
        self.username_label = QtWidgets.QLabel(self.profile_layout_widget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.username_label.sizePolicy().hasHeightForWidth())
        self.username_label.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("123Marker")
        font.setPointSize(16)
        self.username_label.setFont(font)
        self.username_label.setScaledContents(False)
        self.username_label.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.username_label.setWordWrap(False)
        self.username_label.setObjectName("username_label")
        self.username_label.setFixedSize(184, 59)
        self.username_label.setText(f"{self.username}")
        self.left_layout.addWidget(self.username_label)

        # Set up of biography
        self.biography_label = QtWidgets.QLabel(self.profile_layout_widget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.biography_label.sizePolicy().hasHeightForWidth())
        self.biography_label.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("MS Shell Dlg 2")
        font.setPointSize(10)
        self.biography_label.setFont(font)
        self.biography_label.setObjectName("biography_label")
        self.biography_label.setFixedSize(200, 58)
        self.biography_label.setText(f"{self.biography}")
        self.left_layout.addWidget(self.biography_label)

        # Set up of down layout (posts, followers)
        self.down_layout = QtWidgets.QHBoxLayout()
        self.down_layout.setObjectName("down_layout")

        # Set up of posts layout
        self.posts_layout = QtWidgets.QVBoxLayout()
        self.posts_layout.setObjectName("posts_layout")

        # Set up of username
        self.posts_label = QtWidgets.QLabel(self.profile_layout_widget)
        font = QtGui.QFont()
        font.setFamily("MS Shell Dlg 2")
        font.setPointSize(13)
        font.setBold(False)
        font.setWeight(50)
        self.posts_label.setFont(font)
        self.posts_label.setAlignment(QtCore.Qt.AlignCenter)
        self.posts_label.setObjectName("posts_label")
        self.posts_label.setFixedSize(94, 27)
        self.posts_label.setText("Posts")
        self.posts_layout.addWidget(self.posts_label)

        # Set up of number of posts
        self.noPosts_label = QtWidgets.QLabel(self.profile_layout_widget)
        font = QtGui.QFont()
        font.setPointSize(14)
        self.noPosts_label.setFont(font)
        self.noPosts_label.setAlignment(QtCore.Qt.AlignCenter)
        self.noPosts_label.setObjectName("noPosts_label")
        self.noPosts_label.setFixedSize(94, 28)

        if self.posts < 1000:
            self.noPosts_label.setText(f"{self.posts}")
        else:
            self.noPosts_label.setText(f"{round((self.posts / 1000), 2)}K")
        
        self.posts_layout.addWidget(self.noPosts_label)
        self.down_layout.addLayout(self.posts_layout)

        # Set up of followers layout
        self.followers_layout = QtWidgets.QVBoxLayout()
        self.followers_layout.setObjectName("followers_layout")

        # Set up of followers
        self.followers_label = QtWidgets.QLabel(self.profile_layout_widget)
        font = QtGui.QFont()
        font.setPointSize(13)
        self.followers_label.setFont(font)
        self.followers_label.setAlignment(QtCore.Qt.AlignCenter)
        self.followers_label.setObjectName("followers_label")
        self.followers_label.setFixedSize(93, 27)
        self.followers_label.setText("Followers")
        self.followers_layout.addWidget(self.followers_label)

        # Set up of number of followers
        self.noFollowers_label = QtWidgets.QLabel(self.profile_layout_widget)
        font = QtGui.QFont()
        font.setPointSize(14)
        self.noFollowers_label.setFont(font)
        self.noFollowers_label.setAlignment(QtCore.Qt.AlignCenter)
        self.noFollowers_label.setObjectName("noFollowers_label")
        self.noFollowers_label.setFixedSize(93, 28)
        
        if self. followers < 1000:
            self.noFollowers_label.setText(f"{self. followers}")
        else:
            self.noFollowers_label.setText(f"{round((self. followers / 1000), 2)}K")
        
        self.followers_layout.addWidget(self.noFollowers_label)
        self.down_layout.addLayout(self.followers_layout)
        self.left_layout.addLayout(self.down_layout)
        self.profile_layout.addLayout(self.left_layout)

        # Set up of right layout (buttons and followings)
        self.right_layout = QtWidgets.QVBoxLayout()
        self.right_layout.setObjectName("right_layout")

        # Set up of buttons layout
        self.buttons_layout = QtWidgets.QHBoxLayout()
        self.buttons_layout.setObjectName("buttons_layout")

        # Set up of download button
        self.download_button = QtWidgets.QPushButton(self.profile_layout_widget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.download_button.sizePolicy().hasHeightForWidth())
        self.download_button.setSizePolicy(sizePolicy)
        self.download_button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.download_button.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.download_button.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.download_button.setText("")
        icon = QtGui.QIcon()

        if self.is_profile_downloaded == 1: # If profile is downloaded show update button
            icon.addPixmap(QtGui.QPixmap(path + "/Assets/update.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)

        else: # Else show download button
            icon.addPixmap(QtGui.QPixmap(path + "/Assets/download.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        
        self.download_button.setIcon(icon)
        self.download_button.setIconSize(QtCore.QSize(40, 40))
        self.download_button.setFlat(True)
        self.download_button.setObjectName("download_button")
        self.download_button.setFixedSize(53, 58)
        self.download_button.clicked.connect(self.__download_profile)
        self.buttons_layout.addWidget(self.download_button)

        # Set up of remove button
        self.remove_button = QtWidgets.QPushButton(self.profile_layout_widget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.remove_button.sizePolicy().hasHeightForWidth())
        self.remove_button.setSizePolicy(sizePolicy)
        self.remove_button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.remove_button.setText("")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(path + "/Assets/remove.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.remove_button.setIcon(icon)
        self.remove_button.setIconSize(QtCore.QSize(40, 40))
        self.remove_button.setFlat(True)
        self.remove_button.setObjectName("remove_button")
        self.remove_button.setFixedSize(53, 58)
        self.remove_button.clicked.connect(self.__remove_profile)
        self.buttons_layout.addWidget(self.remove_button)
        self.right_layout.addLayout(self.buttons_layout)

        # Set up of the empty label between buttons and followings
        self.empty_label = QtWidgets.QLabel(self.profile_layout_widget)
        self.empty_label.setText("")
        self.empty_label.setObjectName("empty_label")
        self.empty_label.setFixedSize(115, 59)
        self.right_layout.addWidget(self.empty_label)

        # Set up of following layout
        self.following_layout = QtWidgets.QVBoxLayout()
        self.following_layout.setObjectName("following_layout")

        # Set up of following
        self.following_label = QtWidgets.QLabel(self.profile_layout_widget)
        font = QtGui.QFont()
        font.setPointSize(13)
        self.following_label.setFont(font)
        self.following_label.setAlignment(QtCore.Qt.AlignCenter)
        self.following_label.setObjectName("following_label")
        self.following_label.setFixedSize(113, 27)
        self.following_label.setText("Following")
        self.following_layout.addWidget(self.following_label)

        # Set up of number of followings
        self.noFollowing_label = QtWidgets.QLabel(self.profile_layout_widget)
        font = QtGui.QFont()
        font.setPointSize(14)
        self.noFollowing_label.setFont(font)
        self.noFollowing_label.setAlignment(QtCore.Qt.AlignCenter)
        self.noFollowing_label.setObjectName("noFollowing_label")
        self.noFollowing_label.setFixedSize(113, 28)

        if self.followings < 1000:
            self.noFollowing_label.setText(f"{self.followings}")
        else:
            self.noFollowing_label.setText(f"{round((self.followings / 1000), 2)}K")
        
        self.following_layout.addWidget(self.noFollowing_label)
        self.right_layout.addLayout(self.following_layout)
        self.profile_layout.addLayout(self.right_layout)

        # Set up of view button
        self.view_button = QtWidgets.QPushButton(self.profile_layout_widget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.view_button.sizePolicy().hasHeightForWidth())
        self.view_button.setSizePolicy(sizePolicy)
        self.view_button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.view_button.setText("")
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(path + "/Assets/view.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.view_button.setIcon(icon1)
        self.view_button.setIconSize(QtCore.QSize(30, 30))
        self.view_button.setFlat(True)
        self.view_button.setObjectName("view_button")
        self.view_button.setFixedSize(43, 199)
        self.view_button.clicked.connect(self.__view_profile)
        self.profile_layout.addWidget(self.view_button)

        self.setLayout(self.profile_layout) # Set profile_layout as the widget's layout
    
    def __download_profile(): # Download or update profile
        #TODO: Download or update the profile
        pass

    def __remove_profile(): # Remove the profile
        #TODO: Remove the profile
        pass

    def __view_profile(): # View the profile
        #TODO: View the profile
        pass