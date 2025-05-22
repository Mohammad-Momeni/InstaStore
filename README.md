# InstaStore

**InstaStore** is a Python-based, command-line Instagram full-profile downloader (mass downloader) that doesn’t rely on Instagram’s official API. Instead, it scrapes the web interface using **Zendriver** (a fork of NoDriver that lets you drive Selenium without bundling a browser driver), and stores all of your target profiles and their metadata in a lightweight **SQLite** database.

---

## 🔍 What It Does

- **Profile Management**  
  - `add_profile(username)` – register a new Instagram profile in the local database  
  - `update_profile(username)` – refresh the metadata (e.g. new posts, stories) for an existing profile  

- **Content Download**  
  - `download_posts` – bulk-download every post (photos & videos)  
  - `download_single_highlight_stories` – download all available stories of a highlight or profile's stories  
  - `download_highlights_stories` – download every highlights stories  
  - _…and more functions you can call directly from Python_  

- **Data Storage**  
  - All profiles, their settings, and download history live in a local SQLite file (`storage/data.db` by default).  
  - Media files are saved into structured folders (e.g. `storage/<username>/posts/`, `…/stories/`, etc.), alongside JSON metadata (captions, timestamps, like counts).

---

## ⚙️ Under the Hood

- **Zendriver**: a drop-in replacement for Selenium’s browser driver that spins up a headless Chromium instance without downloading or configuring a separate WebDriver binary.  
- **SQLite**: zero-configuration, file-based database (`sqlite3` stdlib module) to track which profiles you’ve added and what content you’ve already downloaded.  
- **Core Dependencies**:  
  - `selenium` (via Zendriver)  
  - `beautifulsoup4` / `lxml` (for parsing HTML when needed)  
  - `cv2` (for making thumbnails)  
  - `curl_cffi` (for lightweight HTTP calls)  

---

## 🚀 Quick Start

1. **Clone & install**  
   ```bash
   git clone https://github.com/Mohammad-Momeni/InstaStore.git
   cd InstaStore
   ```

2. **Use in your own scripts**  
   ```python
   from main import add_profile, update_profile, download_posts

   # 1) Add a new profile to the database
   add_profile("nasa")

   # 2) Later, update it…
   update_profile("nasa")

   # 3) …and grab all their posts
   download_posts("nasa", is_tag)
   ```

> **Note:** All functions are currently exposed as Python callables—you import the module and invoke them directly. A GUI interface is on the roadmap!

---

## 🎨 GUI Roadmap

A desktop GUI (likely built in PyQt5 or Electron + React) is coming soon. It will let you:

- Enter credentials & target usernames in a friendly form  
- Toggle which content types to archive  
- View download progress in real time  
- Schedule recurring automatic backups  

Watch this space (and the `gui/` branch) for mockups and early previews in the **Assets/** folder.

---

## 📄 License

This project is released under the **GNU AGPL-3.0 License**. See [LICENSE](LICENSE) for full terms.
