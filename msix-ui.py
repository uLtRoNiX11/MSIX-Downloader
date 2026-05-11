import ctypes
import os
import re
import tempfile
import threading
import tkinter.filedialog as fd

import customtkinter as ctk
from curl_cffi import requests
from PIL import Image


# --- Windows Font Loader ---
def load_custom_fonts():
    """Temporarily loads TTF fonts into the Windows session memory."""
    if os.name != "nt":
        return  # Skip if not on Windows

    fonts = ["Geist-Regular.ttf", "Geist-Bold.ttf"]
    FR_PRIVATE = 0x10  # Loads the font only for this application

    for font in fonts:
        font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), font)
        if os.path.exists(font_path):
            ctypes.windll.gdi32.AddFontResourceExW(font_path, FR_PRIVATE, 0)
        else:
            print(
                f"[!] Warning: Custom font file '{font}' not found in the script directory."
            )


# --- Theme Setup ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")


class MSIXDownloader(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("MSIX Downloader")
        self.geometry("600x700")
        self.resizable(False, False)

        # UI Data
        self.bundles_data = {}
        self.current_logo = None
        self.is_downloading = False

        # Typography Setup (Using the loaded Geist fonts)
        self.font_title = ctk.CTkFont(family="Geist", size=22, weight="bold")
        self.font_subheading = ctk.CTkFont(family="Geist", size=12, weight="bold")
        self.font_btn = ctk.CTkFont(family="Geist", size=14, weight="bold")

        self.font_main = ctk.CTkFont(family="Geist", size=14, weight="normal")
        self.font_small = ctk.CTkFont(family="Geist", size=12, weight="normal")
        self.font_tiny = ctk.CTkFont(family="Geist", size=11, weight="normal")

        self.setup_ui()

    def setup_ui(self):
        # --- Top Header Frame (Logo & App Info) ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent", height=80)
        self.header_frame.pack(fill="x", padx=40, pady=(25, 15))
        self.header_frame.pack_propagate(False)

        self.info_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.info_frame.pack(side="left", fill="both", expand=True)

        self.lbl_app_name = ctk.CTkLabel(
            self.info_frame, text="MSIX Downloader", font=self.font_title, anchor="w"
        )
        self.lbl_app_name.pack(fill="x", pady=(10, 0))

        self.lbl_publisher = ctk.CTkLabel(
            self.info_frame,
            text="Enter an App ID below to begin.",
            text_color="gray",
            font=self.font_small,
            anchor="w",
        )
        self.lbl_publisher.pack(fill="x")

        self.logo_label = ctk.CTkLabel(self.header_frame, text="", width=80, height=80)
        self.logo_label.pack(side="right", padx=(15, 0))

        # --- Input Frame ---
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.pack(fill="x", padx=40)

        self.entry_appid = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="Enter App ID (e.g., 9nbdxk71nk08)",
            font=self.font_main,
            height=40,
        )
        self.entry_appid.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_search = ctk.CTkButton(
            self.input_frame,
            text="Search",
            font=self.font_btn,  # Bold Button Font
            width=100,
            height=40,
            command=self.start_search,
        )
        self.btn_search.pack(side="right")

        # --- Results Dropdown ---
        self.combo_results = ctk.CTkOptionMenu(
            self,
            values=["Awaiting search..."],
            font=self.font_main,
            dropdown_font=self.font_main,
            state="disabled",
            height=40,
            dynamic_resizing=False,
            command=self.on_file_select,
        )
        self.combo_results.pack(fill="x", padx=40, pady=(20, 10))

        # --- Metadata Frame ---
        self.meta_frame = ctk.CTkFrame(
            self, fg_color=("gray90", "gray13"), corner_radius=8
        )
        self.meta_frame.pack(fill="x", padx=40, pady=(0, 20), ipady=10, ipadx=15)

        self.lbl_meta_title = ctk.CTkLabel(
            self.meta_frame, text="File Metadata", font=self.font_subheading, anchor="w"
        )  # Bold Subheading
        self.lbl_meta_title.pack(fill="x", pady=(5, 5))

        self.lbl_meta_appid = ctk.CTkLabel(
            self.meta_frame,
            text="App ID: --",
            font=self.font_small,
            anchor="w",
            text_color="gray",
        )
        self.lbl_meta_appid.pack(fill="x")

        self.lbl_size = ctk.CTkLabel(
            self.meta_frame,
            text="Size: --",
            font=self.font_small,
            anchor="w",
            text_color="gray",
        )
        self.lbl_size.pack(fill="x")

        self.lbl_sha1 = ctk.CTkLabel(
            self.meta_frame,
            text="SHA-1: --",
            font=self.font_tiny,
            anchor="w",
            text_color="gray",
        )
        self.lbl_sha1.pack(fill="x")

        self.lbl_expire = ctk.CTkLabel(
            self.meta_frame,
            text="Link Expires: --",
            font=self.font_small,
            anchor="w",
            text_color="gray",
        )
        self.lbl_expire.pack(fill="x")

        # --- Save Location Frame ---
        self.save_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.save_frame.pack(fill="x", padx=40, pady=(0, 10))

        self.lbl_save = ctk.CTkLabel(
            self.save_frame,
            text="Save Location:",
            font=self.font_small,
            text_color="gray",
            anchor="w",
        )
        self.lbl_save.pack(fill="x")

        self.path_container = ctk.CTkFrame(self.save_frame, fg_color="transparent")
        self.path_container.pack(fill="x")

        self.entry_path = ctk.CTkEntry(
            self.path_container, font=self.font_main, height=35
        )
        default_dl = os.path.join(os.path.expanduser("~"), "Downloads")
        self.entry_path.insert(0, default_dl)
        self.entry_path.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_browse = ctk.CTkButton(
            self.path_container,
            text="Browse",
            font=self.font_btn,  # Bold Button Font
            width=80,
            height=35,
            command=self.browse_folder,
        )
        self.btn_browse.pack(side="right")

        # --- Progress Section ---
        self.progress_bar = ctk.CTkProgressBar(self, height=8, corner_radius=4)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=40, pady=(10, 5))

        self.label_status = ctk.CTkLabel(
            self, text="Ready.", text_color="gray", font=self.font_small
        )
        self.label_status.pack()

        # --- Download/Cancel Button ---
        self.btn_download = ctk.CTkButton(
            self,
            text="Download Bundle",
            font=self.font_btn,  # Bold Button Font
            height=45,
            state="disabled",
            command=self.start_download,
        )
        self.btn_download.pack(pady=(15, 0))

    # --- Interaction Events ---
    def browse_folder(self):
        folder_selected = fd.askdirectory(title="Select Download Folder")
        if folder_selected:
            self.entry_path.delete(0, ctk.END)
            self.entry_path.insert(0, os.path.normpath(folder_selected))

    def on_file_select(self, selected_filename):
        meta = self.bundles_data.get(selected_filename)
        if meta:
            self.lbl_size.configure(text=f"Size: {meta['size']}")
            self.lbl_sha1.configure(text=f"SHA-1: {meta['sha1']}")
            self.lbl_expire.configure(text=f"Link Expires: {meta['expire']}")

    def start_search(self):
        app_id = self.entry_appid.get().strip()
        if not app_id:
            self.label_status.configure(text="Please enter an App ID.")
            return

        self.btn_search.configure(state="disabled")
        self.btn_download.configure(state="disabled")
        self.label_status.configure(text="Querying Microsoft servers...")
        self.combo_results.configure(values=["Searching..."], state="disabled")
        self.combo_results.set("Searching...")

        self.lbl_size.configure(text="Size: --")
        self.lbl_sha1.configure(text="SHA-1: --")
        self.lbl_expire.configure(text="Link Expires: --")
        self.logo_label.configure(image=None)
        self.lbl_app_name.configure(text="Loading metadata...")
        self.lbl_publisher.configure(text="")

        threading.Thread(
            target=self.fetch_links_task, args=(app_id,), daemon=True
        ).start()

    def start_download(self):
        filename = self.combo_results.get()
        meta = self.bundles_data.get(filename)
        save_directory = self.entry_path.get().strip()

        if not meta or not save_directory:
            return

        if not os.path.isdir(save_directory):
            self.label_status.configure(
                text="Error: The specified save location is invalid."
            )
            return

        full_save_path = os.path.join(save_directory, filename)

        self.btn_search.configure(state="disabled")
        self.btn_browse.configure(state="disabled")
        self.combo_results.configure(state="disabled")
        self.progress_bar.set(0)

        self.is_downloading = True
        self.btn_download.configure(
            text="Cancel",
            command=self.cancel_download,
            fg_color="#B22222",
            hover_color="#8B0000",
        )

        threading.Thread(
            target=self.download_task, args=(meta["url"], full_save_path), daemon=True
        ).start()

    def cancel_download(self):
        self.is_downloading = False
        self.btn_download.configure(state="disabled")
        self.label_status.configure(text="Cancelling download...")

    # --- Background Tasks ---
    def fetch_store_metadata(self, app_id):
        try:
            url = f"https://apps.microsoft.com/detail/{app_id}?hl=en-us&gl=US"
            r = requests.get(url, impersonate="chrome", timeout=10)
            if r.status_code == 200:
                html = r.text
                name = re.search(r"<title>(.*?)\s*-", html)
                icon = re.search(r'<meta property="og:image" content="([^"]+)"', html)

                if name and icon:
                    app_name = name.group(1).strip()
                    icon_url = icon.group(1).strip()
                    return app_name, "Microsoft Store", icon_url
        except Exception:
            pass

        try:
            url = f"https://displaycatalog.mp.microsoft.com/v7.0/products/{app_id}?market=US&languages=en-US&MS-CV=DUMMY.1"
            r = requests.get(url, impersonate="chrome", timeout=10)
            if r.status_code == 200:
                data = r.json()
                props = data.get("Products", [])[0].get("LocalizedProperties", [])[0]

                name = props.get("ProductTitle", "Unknown App")
                publisher = props.get("PublisherName", "Unknown Publisher")

                icon_url = None
                for img in props.get("Images", []):
                    if img.get("ImagePurpose") in ["Tile", "Logo", "AppIcon"]:
                        icon_url = "https:" + img.get("Uri")
                        break
                return name, publisher, icon_url
        except Exception:
            pass

        return None, None, None

    def fetch_links_task(self, app_id):
        app_name, publisher, icon_url = self.fetch_store_metadata(app_id)

        img_pil = None
        if icon_url:
            try:
                img_data = requests.get(
                    icon_url, impersonate="chrome", timeout=10
                ).content
                icon_path = os.path.join(tempfile.gettempdir(), f"{app_id}_icon.png")
                with open(icon_path, "wb") as f:
                    f.write(img_data)
                img_pil = Image.open(icon_path).convert("RGBA")
            except Exception:
                pass

        self.after(0, self._sync_header_ui, app_name, publisher, img_pil, app_id)

        url = "https://store.rg-adguard.net/api/GetFiles"
        payload = {
            "type": "ProductId",
            "url": app_id,
            "ring": "Retail",
            "lang": "en-US",
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://store.rg-adguard.net",
            "Referer": "https://store.rg-adguard.net/",
        }

        try:
            response = requests.post(
                url, data=payload, headers=headers, impersonate="chrome", timeout=15
            )
            response.raise_for_status()

            pattern = re.compile(
                r'<a href="([^"]+)"[^>]*>([^<]+)</a></td>\s*<td[^>]*>([^<]*)</td>\s*<td[^>]*>([^<]*)</td>\s*<td[^>]*>([^<]*)</td>'
            )
            matches = pattern.findall(response.text)

            self.bundles_data = {}
            for link, filename, expire, sha1, size in matches:
                if filename.endswith((".msixbundle", ".appxbundle")):
                    self.bundles_data[filename] = {
                        "url": link,
                        "size": size.strip(),
                        "expire": expire.strip(),
                        "sha1": sha1.strip(),
                    }

            if not self.bundles_data:
                self.after(
                    0, self.update_ui_after_search, False, None, "No .msixbundle found."
                )
                return

            filenames = list(self.bundles_data.keys())
            self.after(0, self.update_ui_after_search, True, filenames, "")

        except Exception as e:
            self.after(0, self.update_ui_after_search, False, None, f"Error: {str(e)}")

    def download_task(self, url, filepath):
        try:
            r = requests.get(url, stream=True, impersonate="chrome", timeout=20)
            r.raise_for_status()

            total_length = r.headers.get("content-length")
            cancelled_by_user = False

            with open(filepath, "wb") as f:
                if total_length is None:
                    self.after(
                        0, self._sync_dl_progress, 0, "Downloading... (Unknown Size)"
                    )
                    for chunk in r.iter_content(chunk_size=8192):
                        if not self.is_downloading:
                            cancelled_by_user = True
                            break
                        if chunk:
                            f.write(chunk)
                else:
                    dl = 0
                    total_length = int(total_length)
                    for chunk in r.iter_content(chunk_size=8192):
                        if not self.is_downloading:
                            cancelled_by_user = True
                            break
                        if chunk:
                            dl += len(chunk)
                            f.write(chunk)

                            progress = dl / total_length
                            mb_dl = dl // (1024 * 1024)
                            mb_tot = total_length // (1024 * 1024)
                            text = f"Downloading: {mb_dl}MB / {mb_tot}MB"
                            self.after(0, self._sync_dl_progress, progress, text)

            if cancelled_by_user:
                if os.path.exists(filepath):
                    os.remove(filepath)
                self.after(
                    0,
                    self.update_ui_after_download,
                    False,
                    "",
                    "Download cancelled by user.",
                )
            else:
                self.after(0, self.update_ui_after_download, True, filepath, "")

        except Exception as e:
            self.after(0, self.update_ui_after_download, False, "", str(e))

    # --- UI Safe Updaters ---
    def _sync_header_ui(self, app_name, publisher, img_pil, app_id):
        self.lbl_app_name.configure(
            text=app_name if app_name else "Unknown Application"
        )
        self.lbl_publisher.configure(text=publisher if publisher else "Microsoft Store")
        self.lbl_meta_appid.configure(text=f"App ID: {app_id}")

        if img_pil:
            self.current_logo = ctk.CTkImage(
                light_image=img_pil, dark_image=img_pil, size=(80, 80)
            )
            self.logo_label.configure(image=self.current_logo)
        else:
            self.current_logo = None
            self.logo_label.configure(image=None)

    def _sync_dl_progress(self, progress, text):
        self.progress_bar.set(progress)
        self.label_status.configure(text=text)

    def update_ui_after_search(self, success, data, msg):
        self.btn_search.configure(state="normal")

        if success:
            self.combo_results.configure(values=data, state="normal")
            self.combo_results.set(data[0])
            self.btn_download.configure(state="normal")
            self.label_status.configure(text=f"Found {len(data)} bundle(s).")
            self.on_file_select(data[0])
        else:
            self.combo_results.configure(values=["No results"], state="disabled")
            self.combo_results.set("No results")
            self.label_status.configure(text=msg)

    def update_ui_after_download(self, success, filepath, msg):
        self.btn_search.configure(state="normal")
        self.btn_browse.configure(state="normal")
        self.combo_results.configure(state="normal")

        default_color = ctk.ThemeManager.theme["CTkButton"]["fg_color"]
        default_hover = ctk.ThemeManager.theme["CTkButton"]["hover_color"]
        self.btn_download.configure(
            text="Download Bundle",
            command=self.start_download,
            state="normal",
            fg_color=default_color,
            hover_color=default_hover,
        )

        if success:
            self.label_status.configure(text=f"Saved to: {filepath}")
            self.progress_bar.set(1.0)
        else:
            self.label_status.configure(text=msg)
            self.progress_bar.set(0)


if __name__ == "__main__":
    # Pre-load custom fonts into memory before building the UI
    load_custom_fonts()

    app = MSIXDownloader()
    app.mainloop()
