import customtkinter as ctk
import yt_dlp
import os
import re

def download_audio():
    url = url_entry.get()
    # Validate URL format
    if not url or not re.match(r'https?://(www\.)?(youtube|youtu|vimeo)\.(com|tv)/', url):
        status_label.configure(text="❌ Please enter a valid YouTube URL", text_color="red")
        return
    
    status_label.configure(text="⏳ Downloading...", text_color="yellow")
    app.update_idletasks()
    
    # Set download folder
    download_folder = os.path.join(os.path.expanduser("~"), "Music")
    os.makedirs(download_folder, exist_ok=True)
    
    # Define yt-dlp options for audio extraction
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(download_folder, '%(title)s.%(ext)s'),
        # Enable playlist downloads by removing 'noplaylist': True
    }
    
    try:
        # Start the download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        status_label.configure(text="✅ Download completed!", text_color="green")
        
        # Clear the URL input field after download
        url_entry.delete(0, ctk.END)  # Clear input field
    
    except yt_dlp.DownloadError as e:
        # Handle download errors
        status_label.configure(text=f"❌ Download error: {str(e)}", text_color="red")
    except Exception as e:
        # Handle other errors
        status_label.configure(text=f"❌ Error: {str(e)}", text_color="red")

# UI Setup
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("YouTube Converter - Manu OVG")
app.geometry("500x350")
app.iconbitmap("youtube_icon.ico")  # Set the window icon

# Header label
ctk.CTkLabel(app, text="🎵 YouTube to MP3", font=("Arial", 20)).pack(pady=10)

# Author label
ctk.CTkLabel(app, text="Created by Manu OVG", font=("Arial", 12)).pack(pady=5)

# URL input field
url_entry = ctk.CTkEntry(app, placeholder_text="Enter YouTube video URL or Playlist URL", width=400)
url_entry.pack(pady=10)

# Download button
download_button = ctk.CTkButton(app, text="Download", command=download_audio)
download_button.pack(pady=10)

# Status label
status_label = ctk.CTkLabel(app, text="")
status_label.pack(pady=10)

app.mainloop()
