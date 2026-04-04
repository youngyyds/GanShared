# Copyright (c) 2026 youngyyds
# Licensed under the MIT License. See LICENSE file for details

from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
import tkinter as tk
import dialog # ./GanShared/dialog.py
import os
import getpass
import sys
import re
import socket
import threading
import json
import ipaddress
import subprocess
import hashlib
from tkinterdnd2 import DND_FILES, TkinterDnD
import ssl
import platform

__version__ = "1.0" 

__doc__ = """
GanShared is a cross-platform file sharing software based on Python, 
which supports file upload, download, deletion, search, breakpoint continuation, 
encrypted transmission, and server management functions.

Features:
1. Connect/disconnect server
2. Upload file (support multiple file upload, large file transmission)
3. Download file
4. Delete file
5. Auto-refresh file list
6. Configurable json file
7. Set password, username, IP address (All in server management)
"""        

class InitApp:
    def init_userdata(self):
        os.makedirs(self.data_folder_path, exist_ok=True)
        
        # If the configuration file does not exist, create a default configuration
        if not os.path.exists(self.userdata_file):
            self.userdata_json = {}
            with open(self.userdata_file, "w", encoding="utf-8") as f:
                json.dump(self.userdata_json, f, indent=4)
                f.close()
            return
        
        # Attempt to load the configuration file
        
        while True:
            try:
                with open(self.userdata_file, "r", encoding="utf-8") as f:
                    if os.path.getsize(self.userdata_file) == 0:
                        self.userdata_json = {}
                    else:
                        self.userdata_json = json.load(f)
                    f.close()

                return  # 加载成功
                
            except Exception as e:
                response = messagebox.askyesnocancel("GanShared", 
                    f"Configuration file is damaged.\n\n"
                    f"Error: {str(e)}\n\n"
                    f"Options:\n"
                    f"• Yes: Reset configuration file\n"
                    f"• No: Manually edit configuration file\n"
                    f"• Cancel: Exit program")
                    
                if response is None:  # Cancel
                    sys.exit(0)
                elif response:  # Yes - Reset
                    self.userdata_json = {}
                    with open(self.userdata_file, "w", encoding="utf-8") as f:
                        json.dump(self.userdata_json, f, indent=4)
                        f.close()
                    return
                else:  # No - Manual edit
                    try:
                        subprocess.run(["notepad.exe", self.userdata_file])
                    except Exception as edit_error:
                        messagebox.showerror("GanShared", f"Cannot open configuration file: {edit_error}")
    
    def get_every_download_chunk(self) -> int:
        if not "download_chunk" in self.userdata_json:
            self.userdata_json["download_chunk"] = self.format_filesize_to_bytes("12MB")
            return self.userdata_json["download_chunk"]
        
        return self.userdata_json["download_chunk"]
        
    def get_every_upload_chunk(self) -> int:
        if not "upload_chunk" in self.userdata_json:
            self.userdata_json["upload_chunk"] = self.format_filesize_to_bytes("12MB")
            return self.userdata_json["upload_chunk"]
        
        return self.userdata_json["upload_chunk"]

    def get_refresh_interval(self) -> int:
        if not "refresh_interval" in self.userdata_json:
            self.userdata_json["refresh_interval"] = 10
            return self.userdata_json["refresh_interval"]
        
        return self.userdata_json["refresh_interval"]
    
    def tk_var_init(self):
        if not "remove_not_message" in self.userdata_json:
            self.userdata_json["remove_not_message"] = 0
            
        if not "entry_mode" in self.userdata_json:
            self.userdata_json["entry_mode"] = "Predictive search mode"
        
        if not "enter_search" in self.userdata_json:
            self.userdata_json["enter_search"] = True
        
        self.remove_not_message = tk.IntVar(value=self.userdata_json["remove_not_message"])
        self.enter_search = tk.IntVar(value=self.userdata_json["enter_search"])
        self.entry_mode = tk.StringVar(value=self.userdata_json["entry_mode"])
        
    def init_app(self) -> bool:
        self.system_username = getpass.getuser()
        if sys.platform == "win32":
            self.data_folder_path = os.path.join(os.path.expanduser("~"), "AppData", "Local", "GanShared")
        elif sys.platform == "linux":
            self.data_folder_path = os.path.join(os.path.expanduser("~"), ".local", "share", "GanShared")
        elif sys.platform == "darwin":
            self.data_folder_path = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "GanShared")

        self.port = 45622
        self.upload_max_size = self.format_filesize_to_bytes("32GB") # 32GB

        if getattr(sys, 'frozen', False):
            self.core_dir = os.path.dirname(sys.executable)
            self.is_exe_environment = True
        else:
            self.core_dir = os.path.dirname(os.path.abspath(__file__))
            self.is_exe_environment = False
        
        self.hidden_items = set()
        self.is_connected = False
        self.auto_refresh_id = None
        self.is_refreshing = False
        # Operation state flags: used to prevent auto-refresh UI restore from interrupting ongoing operations
        self.is_uploading = False
        self.is_downloading = False
        self.is_removing = False
        self.userdata_file = os.path.join(self.data_folder_path, "userdata.json")
        self.password_file = os.path.join(os.path.expanduser("~"), "pwd.ini")
        self.userdata_json = {}
        self.file_items = {}  # item_id: (parent, index, data)
        
        self.init_userdata()
        
        if not ("server_data" in self.userdata_json):
            self.userdata_json["server_data"] = {}
        if not ("last_server" in self.userdata_json):
            self.userdata_json["last_server"] = ""
            self.username = None
            self.ip_address = None
        else:
            try:
                self.username = self.userdata_json["server_data"][self.userdata_json["last_server"]]["username"]
                self.ip_address = self.userdata_json["last_server"]
            except:
                self.username = None
                self.ip_address = None

        self.download_chunk  = self.get_every_download_chunk()
        self.upload_chunk = self.get_every_upload_chunk()
        self.refresh_interval = self.get_refresh_interval()

        self.tk_var_init()
        
        if self.get_password() == False:
            return False
        
        return True
    
    def get_password(self) -> bool: 
        if os.path.exists(self.password_file):
            with open(self.password_file, "r", encoding="utf-8") as f:
                password = f.read()
                f.close()
            
            while True:
                input_password = dialog.askstring("GanShared", f"Hello, {self.username}! Please enter your password: ")
                
                if input_password == None:
                    return False
                
                if len(input_password) > 48:
                    messagebox.showinfo("GanShared", "The password you entered is too long")
                    continue
                
                if hashlib.sha256(input_password.encode()).hexdigest() != password:
                    messagebox.showinfo("GanShared", "Incorrect password")
                    continue

                break
        
        return True

class AppHelp:
    def show_about(self):
        messagebox.showinfo("About", f"GanShared {__version__}\n\n"
                            "Author: youngyyds\n"
                            "Email: younggan2014@outlook.com\n"
                            "Github: https://github.com/youngyyds/GanShared\n"
                            "License: MIT"
                            "Copyright: © 2026 young\n\n"
                            ""
                            "This program is free software: you can redistribute it and/or modify\n")
    def quick_start(self):
        quick_start_window = tk.Toplevel(self)
        quick_start_window.title("Quick start")
        
        height = int((self.winfo_screenheight() - 300) / 2)
        width = int((self.winfo_screenwidth() - 480) / 2)
        
        quick_start_window.geometry(f"480x300+{width}+{height}")

        quick_start_window.resizable(False, False)
        quick_start_window.grab_set()
        
        quick_start_text = tk.Text(quick_start_window, width=40, height=20)
        quick_start_text.pack(fill=tk.BOTH, expand=True)
        
        quick_start_text.insert(tk.END, "1. Create a new server in the server management window\n")
        quick_start_text.insert(tk.END, "2. Connect to a server\n")
        quick_start_text.insert(tk.END, "3. Upload files\n")
        quick_start_text.insert(tk.END, "4. Download files\n")
        quick_start_text.insert(tk.END, "5. Delete files\n")
        quick_start_text.insert(tk.END, "6. Refresh file list\n")
        quick_start_text.insert(tk.END, "7. Configure settings\n")
        quick_start_text.insert(tk.END, "8. Enjoy!\n")
        
        quick_start_text.config(state=tk.DISABLED, font=("Microsoft YaHei", 12, "bold"))
        
        quick_start_window.mainloop()
    
class AppCreateTopUI:
    def create_main_frame(self):
        self.main_frame = ttk.Frame(self, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
    
    def create_button_entry_frame(self):
        # Button frame
        button_entry_frame = ttk.Frame(self.main_frame)
        button_entry_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.connect_button = ttk.Button(
            button_entry_frame, 
            text="Connect", 
            command=self.start_connect,
            takefocus=False
        )
        self.connect_button.pack(side=tk.LEFT, padx=5)
        
        self.disconnect_button = ttk.Button(
            button_entry_frame, 
            text="Disconnect", 
            command=self.start_disconnect,
            state=tk.DISABLED,
            takefocus=False
        )
        self.disconnect_button.pack(side=tk.LEFT, padx=5)
        
        # Refresh button
        self.refresh_button = ttk.Button(
            button_entry_frame, 
            text="Refresh", 
            command=self.start_show_shared_file_information,
            takefocus=False,
            state=tk.DISABLED
        )
        
        self.refresh_button.pack(side=tk.LEFT, padx=5)
        
        # Upload button
        self.upload_button = ttk.Button(
            button_entry_frame, 
            text="Upload", 
            command=self.start_upload_file,
            takefocus=False,
            state=tk.DISABLED
        )
        self.upload_button.pack(side=tk.LEFT, padx=5)

        search_frame = ttk.Frame(button_entry_frame)
        search_frame.pack(side=tk.RIGHT, padx=5)
        
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.on_search_change)
        
        self.search_entry = ttk.Combobox(
            search_frame,
            textvariable=self.search_var,
            width=25,
            state=tk.DISABLED
        )
        self.search_entry.pack(side=tk.LEFT, padx=2)
        self.search_entry.bind("<Return>", self.on_search)
        
        self.search_button = ttk.Button(
            search_frame,
            text="Search",
            command=self.on_search,
            takefocus=False,
            state=tk.DISABLED
        )
        self.search_button.pack(side=tk.LEFT, padx=2)
        
        self.clear_search_button = ttk.Button(
            search_frame,
            text="Clear",
            command=self.clear_search,
            takefocus=False,
            state=tk.DISABLED
        )
        
        self.clear_search_button.pack(side=tk.LEFT, padx=2)
        
    def create_menu(self):
        # Right-click menu
        self.pop_menu = tk.Menu(self, tearoff=False)
        self.pop_menu.add_command(label="Download", command=self.start_download_file)
        self.pop_menu.add_command(label="Remove", command=self.start_remove_file)
        self.pop_menu.add_separator()
        self.pop_menu.add_command(label="Copy filename", command=self.copy_filename)
            
        
        # Main menu
        self.main_menu = tk.Menu(self, tearoff=False)
        # "Set" menu
        self.set_menu = tk.Menu(self.main_menu, tearoff=False)
        self.help_menu = tk.Menu(self.main_menu, tearoff=False)
        
        self.help_menu.add_command(label="About", command=self.show_about)
        self.help_menu.add_command(label="Quick start", command=self.quick_start)
        self.input_box_mode = tk.Menu(self.main_menu, tearoff=False)
        
        self.file_tree_view.drop_target_register(DND_FILES)
        self.file_tree_view.dnd_bind('<<Drop>>', self.pass_drop_event)
        
        self.main_menu.add_cascade(label="Set", menu=self.set_menu)
        self.main_menu.add_cascade(label="Help", menu=self.help_menu)
        
        self.set_menu.add_command(label="Password settings", command=self.set_password)
        self.set_menu.add_command(label="Server management", command=self.show_server_management)
        
        self.set_menu.add_separator()
        
        self.set_menu.add_command(label="Set the size of chunks to upload", command=self.set_upload_chunk)
        self.set_menu.add_command(label="Set the size of chunks to download", command=self.set_download_chunk)
        self.set_menu.add_command(label="Set refresh interval", command=self.set_refresh_interval)
        self.set_menu.add_cascade(label="Set browse input box mode", menu=self.input_box_mode)
        
        self.input_box_mode.add_radiobutton(label="All files mode", variable=self.entry_mode, command=self.set_preview)
        self.input_box_mode.add_radiobutton(label="Predictive search mode", variable=self.entry_mode, command=self.set_preview)
        
        self.set_menu.add_separator()
        
        self.set_menu.add_checkbutton(label="Do not prompt when removing files", variable=self.remove_not_message, 
                                      command = self.remove_not_message_do)
        self.set_menu.add_checkbutton(label="Real-time search", variable=self.enter_search, 
                                      command = self.set_enter_search)
        
        self.set_menu.add_separator()
        
        self.set_menu.add_command(label="Exit", command=self.on_closing)
        
        self.config(menu=self.main_menu)
    
    def create_other(self):
        # Status bar
        self.status_bar = ttk.Label(
            self, 
            text="Status: Disconnected", 
            relief=tk.SUNKEN, 
            anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def create_tree_frame(self):
        # File list frame
        tree_frame = ttk.LabelFrame(self.main_frame, text="Shared Files", padding="5")
        tree_frame.pack(fill=tk.BOTH, expand=True)
    
        # Treeview
        self.file_tree_view = ttk.Treeview(
            tree_frame, 
            columns=["Filename", "Send_user", "Send_time", "Size"], 
            show="headings",
            selectmode="browse"
        )
        
        self.file_tree_view.heading("Filename", text="Filename")
        self.file_tree_view.heading("Send_user", text="Uploaded By")
        self.file_tree_view.heading("Send_time", text="Upload Time")
        self.file_tree_view.heading("Size", text="Size")
        
        
        self.file_tree_view.column("Filename", width=300)
        self.file_tree_view.column("Send_user", width=200)
        self.file_tree_view.column("Send_time", width=100)
        self.file_tree_view.column("Size", width=100)
        
        
        vbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.file_tree_view.yview)
        hbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.file_tree_view.xview)
        self.file_tree_view.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        
        self.file_tree_view.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
    def create_ui(self):
        self.create_main_frame()
        self.create_button_entry_frame()
        self.create_tree_frame()
        self.create_menu()
        self.create_other()

class AppTools:
    def get_cert_password(self) -> str:
        import secret
        
        return secret.decrypt_aes(secret.client_cert, hashlib.md5(platform.processor().encode()).hexdigest())
    
    def del_illegal_chars(self, chars: str) -> str:
        return re.sub(r'[\n\r\t\0]', "", re.sub(r'[<>:"/\\|?*]', "_", chars))
    
    def recv_exact(self, sock: socket.socket, n: int) -> bytes:
        data = bytearray()
        while len(data) < n:
            part = sock.recv(n - len(data))
            if not part:
                raise ConnectionError("Socket closed during recv_exact")
            data.extend(part)
        return bytes(data)
    
    def copy_to_clipboard(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)
    
    def find_id_by_content(self, content: str) -> (str | None):
        for iid in self.file_tree_view.get_children():
            values = self.file_tree_view.item(iid, "values")
            if content in values:
                return iid
        return None
    
    def format_filesize_to_bytes(self, format_filesize: str) -> int:
        try:
            # Remove spaces and convert to uppercase
            size_str = format_filesize.strip().upper()
            
            # Define unit conversion
            units = {
                'B': 1,
                'KB': 1024, 
                'MB': 1024**2, 
                'GB': 1024**3, 
                'TB': 1024**4
            }
            
            # Separate number and unit
            num_str = ''
            unit_str = ''
            
            for char in size_str:
                if char.isdigit() or char == '.':
                    num_str += char
                else:
                    unit_str += char
            
            if not num_str:
                return 0
            
            # Parse the number
            num = float(num_str) if '.' in num_str else int(num_str)
            
            # Clean up unit string
            unit_str = unit_str.strip()
            if not unit_str or unit_str == 'B':
                return num
            
            # Find matching unit
            for unit in units:
                if unit_str.startswith(unit):
                    return num * units[unit]
            
            return 0
        except Exception:
            return 0
    
    def format_filesize(self, size: int) -> str:
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        index = 0

        while size >= 1024 and index < len(units) - 1:
            size /= 1024
            index += 1
            
        return f"{round(size, 2)}{units[index]}"

    def check_disk_space(self, required_bytes: int) -> bool:
        try:
            import shutil
            # Get available space on the disk of the target path
            total, used, free = shutil.disk_usage(self.data_folder_path)
            return free >= required_bytes
        except Exception as e:
            print(f"Error checking disk space: {e}")
            return False
   
class AppPermissionManager:
    def check_permission(self, sock: socket.socket):
        pass
    
class AppNetwork:
    def close_connect(self, show_message: str = None, errormode: bool = False):
        try:  
            if hasattr(self, 'sock') and self.sock:
                self.sock.close() 
        except Exception:
            pass
        
        if self.auto_refresh_id is not None:
            self.after_cancel(self.auto_refresh_id)
            self.auto_refresh_id = None
            
        self.is_refreshing = False
        self.is_connected = False
        
        self.main_menu.entryconfig("Set", state=tk.NORMAL)
        self.main_menu.entryconfig("Help", state=tk.NORMAL)
        self.disconnect_button.config(state=tk.DISABLED)
        
        self.file_tree_view.unbind("<Button-3>")
        self.file_tree_view.unbind("<Double-Button-1>")
        self.file_tree_view.drop_target_register(DND_FILES)
        self.file_tree_view.dnd_bind('<<Drop>>', self.pass_drop_event)
        self.refresh_button.config(state=tk.DISABLED)
        self.upload_button.config(state=tk.DISABLED)
        self.search_entry.config(state=tk.DISABLED)
        self.search_button.config(state=tk.DISABLED)
        self.clear_search_button.config(state=tk.DISABLED)
        self.search_entry.set("")
        
        self.status_bar.config(text="Status: Disconnected")
        self.file_tree_view.delete(*self.file_tree_view.get_children())
        
        if show_message and not errormode:
            messagebox.showinfo("GanShared", show_message)  
        if show_message and errormode:
            messagebox.showerror("GanShared", show_message)    
            
        self.connect_button.config(state=tk.NORMAL)
        
        self.config(cursor="arrow")
        
    def connect_success(self):
        self.is_connected = True
        self.status_bar.config(text="Status: Connected")
        self.main_menu.entryconfig("Set", state=tk.NORMAL)
        self.main_menu.entryconfig("Help", state=tk.NORMAL)
        
        messagebox.showinfo("GanShared", "Connection successful")
        
        self.start_show_shared_file_information()
        
        self.start_auto_refresh()

    def connect_server(self, twice: bool = False):
        if (not self.ip_address) or (self.userdata_json["server_data"].get(self.ip_address) == None):
            self.ip_address = None
            self.username = None
            
            self.after_idle(self.close_connect)
            messagebox.showinfo("GanShared", "Please enter the IP address to connect to")
            self.show_server_management()
            return 
        try:
            self.context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            
            self.context.verify_mode = ssl.CERT_REQUIRED

            self.context.check_hostname = False
            
            try:
                self.context.load_verify_locations(cafile=os.path.join(self.core_dir, "ca.crt"))
                self.context.load_cert_chain(
                    os.path.join(self.core_dir, "client.crt"), 
                    os.path.join(self.core_dir, "client.key"), 
                    password=self.get_cert_password()
                )
            except Exception as e:
                self.sock.close()
                
                messagebox.showerror("GanShared", f"Failed to load certificate file: {e}")
                
                self.after_idle(self.close_connect)
                
                return

            _sock = socket.socket()
            self.sock = self.context.wrap_socket(_sock, server_hostname=self.ip_address)

            self.sock.settimeout(8)
            self.sock.connect((self.ip_address, self.port))

            return_msg = self.sock.recv(16)

            if return_msg == b"DUPLICATE_IP":
                self.sock.close()
                self.after_idle(self.close_connect, "Connection failed: Duplicate user", True)
                return

            elif return_msg == b"KEY_REQUIRED":
                # Use after_idle to show dialog, then get key from dialog
                self.after_idle(self.handle_key_required, not twice)
                return

            elif return_msg == b"VERIFIED":
                self.after_idle(self.connect_success)
                return

            else:
                self.sock.close()
                self.after_idle(self.close_connect, f"Connection failed: Unknown server response ({return_msg})", True)
                return

        except ssl.SSLError:
            self.after_idle(self.close_connect, f"Connection failed\nServer certificate verification failed", True)
        
        except Exception as e:
            self.after_idle(self.close_connect, f"Connection failed\n{e}", True)

    def handle_key_required(self, before_key: bool = True):
        if before_key:
            key = self.userdata_json["server_data"][self.ip_address]["key"]
            
            if key == None:
                if hasattr(self, 'sock'):
                    self.sock.close()
                self.connect_server(True)
                
                return
            
        else:
            key = dialog.askstring(
                "GanShared",
                "Your key is incorrect.\n"
                "Please enter a new key to continue.    "
            )

        try:
            if key == None:
                if hasattr(self, 'sock'):
                    self.sock.close()
                self.after_idle(self.close_connect)
                return
        
            if key == "":
                self.sock.close()
                self.after_idle(self.close_connect, "Connection failed: Key cannot be empty", True)
                return
            
            send_msg = {
                "key": hashlib.sha256(key.encode()).hexdigest(), 
                "do": "auth"
            }
            
            self.sock.sendall(json.dumps(send_msg).encode())
            
            return_keymsg = self.sock.recv(16)
            
            if return_keymsg == b"VERIFIED":  
                if key != self.userdata_json["server_data"][self.ip_address].get("key"):
                    do = messagebox.askyesno("GanShared", "Do you want to update your password?")
                    if do:
                        self.userdata_json["server_data"][self.ip_address] = {
                            "key": key, 
                            "username": self.username
                        }
                self.after_idle(self.connect_success)
                return
            
            elif return_keymsg == b"PWD_ERROR":
                if not before_key:
                    self.after_idle(self.close_connect, "Connection failed: Incorrect key", True)
                    return
                
                self.sock.close()
                
                self.connect_server(True)
                
            elif return_keymsg == b"DUPLICATE_IP":
                self.sock.close()
                self.after_idle(self.close_connect, "Connection failed: Duplicate user", True)
            else:
                self.sock.close()
                self.after_idle(self.close_connect, f"Connection failed: Unknown server response ({return_keymsg})", True)
                
            
        except Exception as e:
            if hasattr(self, "sock"):
                self.sock.close()
            self.after_idle(self.close_connect, f"Connection failed\n{e}", True)

    def start_connect(self):
        self.config(cursor="watch")
        self.connect_button.config(state=tk.DISABLED)
        self.main_menu.entryconfig("Set", state=tk.DISABLED)
        self.main_menu.entryconfig("Help", state=tk.DISABLED)
        
        connect_thread = threading.Thread(target=self.connect_server)
        connect_thread.daemon = True
        connect_thread.start()

class AppEvent:
    def right_click_event(self, event=None):
        try:
            self.file_tree_view.selection()[0]
        except Exception:
            return
        
        self.pop_menu.post(event.x_root, event.y_root)  
    
    def double_left_click_event(self, event=None):
        try:
            self.file_tree_view.selection()[0]
        except Exception:
            return
        
        self.start_download_file()  
    
    def pass_drop_event(self, event=None):
        messagebox.showinfo("GanShared", "Drag and drop is temporarily unavailable")
    
    def drop_event(self, event=None):
        self.begin_upload_file()
        
        all_upload_filepath = tuple(self.tk.splitlist(event.data))
        
        if not all_upload_filepath: 
            self.not_meet_upload_file_requirements()
            return

        for file in all_upload_filepath:
            if os.path.isdir(file):
                messagebox.showinfo("GanShared", f"{os.path.basename(file)}: Cannot upload folders")
                self.not_meet_upload_file_requirements()
                return
            
            if os.path.getsize(file) == 0:
                messagebox.showinfo("GanShared", 
                f"{os.path.basename(file)}: Cannot send an empty file or No permission to access")
                
                self.not_meet_upload_file_requirements()
                return
            
            if os.path.getsize(file) > self.upload_max_size: 
                messagebox.showinfo("GanShared", f"{os.path.basename(file)}:Cannot upload files larger than {self.format_filesize(self.upload_max_size)}")
                self.not_meet_upload_file_requirements()
                return
        
        
        # Initialize cancel event (to allow cancellation during drag-and-drop upload)
        self.upload_cancel_event = threading.Event()

        upload_file_thread = threading.Thread(target=self.upload_file, 
                              args=(all_upload_filepath, ), )
        upload_file_thread.daemon = True 
        upload_file_thread.start()

class AppSet:
    def set_password_message(self, message: str = None, return_set_password: bool = False):
        if message:
            messagebox.showinfo("GanShared", message)
        
        if return_set_password:
            self.set_password()
        
        return

    def first_set_password(self):
        password = dialog.askstring("GanShared", "Please enter your future password: ")
            
        if password == None:
            return
            
        if password == "":
            return self.set_password_message("Password cannot be empty")
            
        if not re.match(r'[<>:"/\\|?*\n\r\t\0]', password) == None:
            return self.set_password_message("The password cannot contain illegal characters")
            
        if len(password) > 48:
            return self.set_password_message("The password cannot be longer than 48 characters")

        with open(self.password_file, "w", encoding="utf-8") as f:
            f.write(hashlib.sha256(password.encode()).hexdigest())
            f.close()
                
        subprocess.run(["attrib", "+s", "+h", self.password_file])
            
        self.set_password_message("Settings saved successfully")

        return
    
    def set_password(self):
        if not os.path.exists(self.password_file):
            return self.first_set_password()
        
        dialog_password = dialog.SimpleDialog(self, "Password settings", ["Change password", "Delete password", "Cancel"], cancel=3)
        
        choose = dialog_password.go()
        
        if choose == 3 or choose == 2:
            return
        
        if choose == 1:
            return self.del_password()

        if choose == 0:
            return self.change_password()
        
    def change_password(self):
        input_old_password = dialog.askstring("GanShared", "Please enter your old password to change your password: ")
            
        if input_old_password == None:
            return self.set_password_message(None, True)

        if input_old_password == "":
            return self.set_password_message("Password cannot be empty", True)

        if len(input_old_password) > 48:
            return self.set_password_message("The password cannot be longer than 48 characters", True)
            
        with open(self.password_file, "r", encoding="utf-8") as f:
            oldpassword = f.read()
            f.close()
        
        if hashlib.sha256(input_old_password.encode()).hexdigest() != oldpassword:
            return self.set_password_message("Incorrect password", True)
        
        newpassword = dialog.askstring("GanShared", "Please enter your new password: ")
        
        if newpassword == None:
            return self.set_password_message(None, True)
        
        if newpassword == input_old_password:
            return self.set_password_message("The new password cannot be the same as the old password", True)

        if not re.match(r'[<>:"/\\|?*\n\r\t\0]', newpassword) == None:
            return self.set_password_message("The password cannot contain illegal characters", True)
            
        if len(newpassword) > 48:
            return self.set_password_message("The password cannot be longer than 48 characters", True)

        os.remove(self.password_file)
        with open(self.password_file, "w", encoding="utf-8") as f:
            f.write(hashlib.sha256(newpassword.encode()).hexdigest())
            f.close()

        return self.set_password_message("Password changed successfully")
    
    def del_password(self):
        inputpassword = dialog.askstring("GanShared", "Please enter the current password to delete the password: ")
            
        if inputpassword == None:
            return self.set_password_message(None, True)
            
        if inputpassword == "":
            return self.set_password_message("Password cannot be empty", True)

        if len(inputpassword) > 48:
            return self.set_password_message("The password cannot be longer than 48 characters", True)
            
        with open(self.password_file, "r", encoding="utf-8") as f:
            password = f.read()
            f.close()
        
        if hashlib.sha256(inputpassword.encode()).hexdigest() != password:
            return self.set_password_message("Incorrect password", True)
        
        if os.path.exists(self.password_file):
            os.remove(self.password_file)
            
        return self.set_password_message("Password deleted successfully")
    
    def set_upload_chunk(self):
        upload_chunk = dialog.askinteger("GanShared", "Please enter the upload chunk size (MB): ", 
                          initialvalue=int(float(self.format_filesize(self.userdata_json["upload_chunk"])[:-2])), 
                          minvalue=1, maxvalue=512)
        if not upload_chunk:
            return
        
        if self.format_filesize_to_bytes(f"{upload_chunk}MB") == self.upload_chunk:
            messagebox.showinfo("GanShared", "Cannot set the same value")
            return
        
        self.userdata_json["upload_chunk"] = self.format_filesize_to_bytes(f"{upload_chunk}MB")
        
        messagebox.showinfo("GanShared", "Changed successful")
    
    def set_refresh_interval(self):
        refresh_interval = dialog.askinteger("GanShared", "Please enter the Refresh interval (seconds): ", 
                          initialvalue=int(self.userdata_json["refresh_interval"]), 
                          minvalue=5, maxvalue=900, other = -1)
        if refresh_interval == None:
            return
        
        if refresh_interval == self.refresh_interval:
            messagebox.showinfo("GanShared", "Cannot set the same value")
            return
        
        self.userdata_json["refresh_interval"] =  refresh_interval
        
        self.refresh_interval = refresh_interval
        
        messagebox.showinfo("GanShared", "Changed successful")
    
    def set_download_chunk(self):
        download_chunk = dialog.askinteger("GanShared", "Please enter the download chunk size (MB): ", 
                          initialvalue=int(float(self.format_filesize(self.userdata_json["download_chunk"])[:-2])), 
                          minvalue=1, maxvalue=512)
        if not download_chunk:
            return
        
        if self.format_filesize_to_bytes(f"{download_chunk}MB") == self.download_chunk:
            messagebox.showinfo("GanShared", "Cannot set the same value")
            return
        
        self.userdata_json["download_chunk"] = self.format_filesize_to_bytes(f"{download_chunk}MB")
        
        messagebox.showinfo("GanShared", "Changed successful")
        
    def remove_not_message_do(self):
        if self.remove_not_message.get() == 0:
            self.userdata_json["remove_not_message"] = False
            return
        
        self.userdata_json["remove_not_message"] = True
    
    def set_preview(self):
        self.userdata_json["entry_mode"] = self.entry_mode.get()
        if self.userdata_json["entry_mode"] == "All files mode":
            self.start_show_shared_file_information()
        else:
            self.filter_file_list()
    
    def set_enter_search(self):
        self.userdata_json["enter_search"] = bool(self.enter_search.get())

class AppServerManagement:
    def show_server_management(self):
        self.server_management_window =  tk.Toplevel(self, takefocus=True)
        
        x = self.winfo_x() + (self.winfo_width() - 350) // 2
        y = self.winfo_y() + (self.winfo_height() - 150) // 2
        
        self.server_management_window.geometry("650x300+{}+{}".format(x, y))
        self.server_management_window.title("Server management")
        self.server_management_window.resizable(False, False)
        self.server_management_window.grab_set()
        
        server_tree_scrollbar = ttk.Scrollbar(self.server_management_window, orient=tk.VERTICAL)
        server_tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.server_tree = ttk.Treeview(self.server_management_window, 
                                columns=["IP Address", "Key", "Username"], show="headings")
        
        self.server_tree.configure(yscrollcommand=server_tree_scrollbar.set)
        server_tree_scrollbar.config(command=self.server_tree.yview)
        
        self.server_tree.heading("IP Address", text="IP Address")
        self.server_tree.heading("Key", text="Key")
        self.server_tree.heading("Username", text="Username")
        
        self.server_tree.column("IP Address", width=150, anchor=tk.CENTER)
        self.server_tree.column("Key", width=150, anchor=tk.CENTER)
        self.server_tree.column("Username", width=150, anchor=tk.CENTER)
        
        self.server_tree.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        ttk.Button(self.server_management_window, text="Delete selected server", 
                   command=self.delete_server, takefocus=False
        ).pack(fill=tk.X)

        ttk.Button(self.server_management_window, text="Delete all servers", 
                   command=self.delete_all_delete_servers, takefocus=False
        ).pack(fill=tk.X)
        
        ttk.Button(self.server_management_window, text="Create new server", 
                   command=self.create_new_server, takefocus=False
        ).pack(fill=tk.X)
        
        ttk.Button(self.server_management_window, text="Change server config"
                   , command = self.change_server, takefocus=False
        ).pack(fill=tk.X)
        
        ttk.Button(self.server_management_window, text="Choose server",
                   command=self.choose_server, takefocus=False
        ).pack(fill=tk.X)
        
        for ip, data in self.userdata_json["server_data"].items():
            if data["key"] == None:
                self.server_tree.insert("", tk.END, values=(ip, "", data["username"]))
            else:
                self.server_tree.insert("", tk.END, values=(ip, data["key"], data["username"]))
    
    def change_server(self):
        try:
            choose_msg = self.server_tree.item(self.server_tree.selection()[0])["values"]
        except Exception:
            messagebox.showinfo("GanShared", "Please select a server to choose", parent=self.server_management_window)
            return
        
        ip_address = dialog.askstring("GanShared", "Please enter the server IP address: ")
        
        if ip_address == None:
            self.server_management_window.grab_set()
            return
        
        if ip_address == "":
            self.server_management_window.grab_set()
            messagebox.showinfo("GanShared", "The IP address cannot be empty", parent=self.server_management_window)
            return
            
        try:
            ipaddress.IPv4Address(ip_address)
        except:
            try:
                ipaddress.IPv6Address(ip_address)
            except:
                self.server_management_window.grab_set()
                messagebox.showinfo("GanShared", "The IP address format is incorrect, please enter in IPv4 or IPv6 format", parent=self.server_management_window)
                return

        key = dialog.askstring("GanShared", f"Please enter the key for {ip_address}: ", parent=self.server_management_window)
        
        if key == None:
            self.server_management_window.grab_set()
            return
        
        username = dialog.askstring("GanShared", f"Please enter the username for {ip_address}: ", parent=self.server_management_window)
        
        if username == None:
            self.server_management_window.grab_set()
            return
        
        if username == "":
            messagebox.showinfo("GanShared", "The username cannot be empty", parent=self.server_management_window)
            self.server_management_window.grab_set()
            return
        
        if len(username) > 24:
            messagebox.showinfo("GanShared", "Username cannot be longer than 24 characters", parent=self.server_management_window)
            self.server_management_window.grab_set()
            return
        
        del self.userdata_json["server_data"][choose_msg[0]]
        
        for item in self.server_tree.get_children():
            dict_item = self.server_tree.item(item)
            
            if choose_msg[0] in dict_item["values"]:
                self.server_tree.delete(item)
                break
        
        self.userdata_json["server_data"][ip_address] = {}
        
        if key == "":
            self.userdata_json["server_data"][ip_address]["key"] = None # null key
            self.server_tree.insert("", tk.END, values=(ip_address, "", username))
        else:
            self.userdata_json["server_data"][ip_address]["key"] = key
            self.server_tree.insert("", tk.END, values=(ip_address, key, username))
        self.userdata_json["server_data"][ip_address]["username"] = username
        
        self.server_management_window.grab_set()
        messagebox.showinfo("GanShared", f"The server key for {ip_address} has been updated successfully", parent=self.server_management_window)
    
    def choose_server(self):
        try:
            choose_msg = self.server_tree.item(self.server_tree.selection()[0])["values"]
        except Exception:
            messagebox.showinfo("GanShared", "Please select a server to choose", parent=self.server_management_window)
            return
        
        self.ip_address = choose_msg[0]
        self.username = choose_msg[2]
        
        self.userdata_json["last_server"] = self.ip_address
        
        messagebox.showinfo("GanShared", f"The server {self.ip_address} has been chosen successfully", parent=self.server_management_window)
        
    def create_new_server(self):
        ip_address = dialog.askstring("GanShared", "Please enter the server IP address: ")
        
        if ip_address == None:
            self.server_management_window.grab_set()
            return
        
        if ip_address == "":
            self.server_management_window.grab_set()
            messagebox.showinfo("GanShared", "The IP address cannot be empty", parent=self.server_management_window)
            return
            
        try:
            ipaddress.IPv4Address(ip_address)
        except:
            try:
                ipaddress.IPv6Address(ip_address)
            except:
                self.server_management_window.grab_set()
                messagebox.showinfo("GanShared", "The IP address format is incorrect, please enter in IPv4 or IPv6 format", parent=self.server_management_window)
                return
        
        if ip_address in self.userdata_json["server_data"]:
            overwrite = messagebox.askokcancel("GanShared", f"A key for {ip_address} already exists. Do you want to overwrite it?", 
                                               icon=messagebox.WARNING, parent=self.server_management_window)
            if not overwrite:
                self.server_management_window.grab_set()
                return

        key = dialog.askstring("GanShared", f"Please enter the key for {ip_address}: ", parent=self.server_management_window)
        
        if key == None:
            self.server_management_window.grab_set()
            return
        
        username = dialog.askstring("GanShared", f"Please enter the username for {ip_address}: ", parent=self.server_management_window)
        
        if username == None:
            self.server_management_window.grab_set()
            return
        
        if username == "":
            messagebox.showinfo("GanShared", "The username cannot be empty", parent=self.server_management_window)
            self.server_management_window.grab_set()
            return
        
        if len(username) > 24:
            messagebox.showinfo("GanShared", "Username cannot be longer than 24 characters", parent=self.server_management_window)
            self.server_management_window.grab_set()
            return
        
        self.userdata_json["server_data"][ip_address] = {}
        
        for item in self.server_tree.get_children():
            dict_item = self.server_tree.item(item)
            
            if ip_address in dict_item["values"]:
                self.server_tree.delete(item)
                break
        
        if key == "":
            self.userdata_json["server_data"][ip_address]["key"] = None # null key
            self.server_tree.insert("", tk.END, values=(ip_address, "", username))
        else:
            self.userdata_json["server_data"][ip_address]["key"] = key
            self.server_tree.insert("", tk.END, values=(ip_address, key, username))
        self.userdata_json["server_data"][ip_address]["username"] = username
        
        self.server_management_window.grab_set()
        messagebox.showinfo("GanShared", f"The server key for {ip_address} has been created/updated successfully", parent=self.server_management_window)
    
    def delete_all_delete_servers(self):
        do = messagebox.askokcancel("GanShared", "Are you sure you want to delete all servers?", 
                                    icon=messagebox.WARNING, parent=self.server_management_window)
        
        if not do:
            return
        
        self.userdata_json["server_data"] = {}
        
        self.server_tree.delete(*self.server_tree.get_children())
        
        messagebox.showinfo("GanShared", "All keys deleted successfully", parent=self.server_management_window)
    
    def delete_server(self):
        try:
            selected_item = self.server_tree.selection()[0]
        except Exception:
            messagebox.showinfo("GanShared", "Please select a server to delete", parent=self.server_management_window)
            return
        
        do = messagebox.askokcancel("GanShared", "Are you sure you want to delete this servers?", 
                                    icon=messagebox.WARNING, parent=self.server_management_window)
        
        if not do:
            return 
        
        ip_address = self.server_tree.item(selected_item, "values")[0]
        
        del self.userdata_json["server_data"][ip_address]
        
        self.server_tree.delete(selected_item)

class AppCreateChildUI:
    def show_upload_progress(self, title: str, filename: str, filesize: int):
        self.upload_progress_window = tk.Toplevel(self)
        self.upload_progress_window.title(f"Uploading {title}")
        self.upload_progress_window.resizable(False, False)
        self.upload_progress_window.grab_set()
        self.upload_progress_window.config(cursor="watch")
        self.upload_progress_window.protocol("WM_DELETE_WINDOW"
                                             , self.cancel_upload)
        
        # Center display
        x = self.winfo_x() + (self.winfo_width() - 350) // 2
        y = self.winfo_y() + (self.winfo_height() - 200) // 2
        self.upload_progress_window.geometry(f"350x180+{x}+{y}")

        
        if len(filename) < 35:
            self.upload_showfilename = tk.Label(self.upload_progress_window, text=f"Uploading: {filename}")
        else:
            self.upload_showfilename = tk.Label(self.upload_progress_window, text=f"Uploading: {filename[0:35]}...")
        
        self.upload_showfilename.pack(pady=5)
        
        self.upload_size_label = tk.Label(self.upload_progress_window, 
                            text=f"Size: {self.format_filesize(filesize)}")
        self.upload_size_label.pack(pady=2)
        
        self.upload_progress_var = tk.IntVar()
        self.upload_progress_bar = ttk.Progressbar(
            self.upload_progress_window, 
            variable=self.upload_progress_var,
            maximum=100
        )
        self.upload_progress_bar.pack(fill=tk.X, padx=20, pady=10)
        
        self.upload_progress_label = tk.Label(self.upload_progress_window, text="0%")
        self.upload_progress_label.pack(pady=5)
        
        # Cancel button
        self.upload_cancel_button = ttk.Button(self.upload_progress_window, text="Cancel", takefocus=False,
                               command=self.cancel_upload)
        self.upload_cancel_button.pack(pady=5)
        self.upload_cancel_button.config(cursor="arrow")

    def show_download_progress(self, filename: str, format_filesize: str):
        self.download_progress_window = tk.Toplevel(self)
        self.download_progress_window.title(f"Downloading {filename}")
        self.download_progress_window.resizable(False, False)
        self.download_progress_window.grab_set()
        self.download_progress_window.config(cursor="watch")
        self.download_progress_window.protocol("WM_DELETE_WINDOW", self.cancel_download)
        
        # Center display
        x = self.winfo_x() + (self.winfo_width() - 350) // 2
        y = self.winfo_y() + (self.winfo_height() - 150) // 2
        self.download_progress_window.geometry(f"350x180+{x}+{y}")
        
        if len(filename) < 35:
            showfilename = tk.Label(self.download_progress_window, text=f"Downloading: {filename}")
        else:
            showfilename = tk.Label(self.download_progress_window, text=f"Downloading: {filename[0:35]}...")
        
        showfilename.pack(pady=5)
        
        size_label = tk.Label(self.download_progress_window, 
                            text=f"Size: {format_filesize}")
        size_label.pack(pady=2)
        
        self.download_progress_var = tk.IntVar()
        self.download_progress_bar = ttk.Progressbar(
            self.download_progress_window, 
            variable=self.download_progress_var,
            maximum=100
        )
        self.download_progress_bar.pack(fill=tk.X, padx=20, pady=10)
        
        self.download_progress_label = tk.Label(self.download_progress_window, text="0%")
        self.download_progress_label.pack(pady=5)
        
        # Cancel button
        self.download_cancel_button = ttk.Button(self.download_progress_window, text="Cancel", takefocus=False,
                             command=self.cancel_download)
        self.download_cancel_button.pack(pady=5)
        self.download_cancel_button.config(cursor="arrow")
    
class AppUpdateTopUI:
    def begin_upload_file(self):
        self.disconnect_button.config(state=tk.DISABLED)
        self.upload_button.config(state=tk.DISABLED)
        self.refresh_button.config(state=tk.DISABLED)
        self.search_entry.config(state=tk.DISABLED)
        self.search_button.config(state=tk.DISABLED)
        self.clear_search_button.config(state=tk.DISABLED)
        
        self.is_uploading = True
    def not_meet_upload_file_requirements(self):
        # Upload not started/finished, clear flags
        self.upload_button.config(state=tk.NORMAL)
        self.refresh_button.config(state=tk.NORMAL)
        self.disconnect_button.config(state=tk.NORMAL)
        self.search_entry.config(state=tk.NORMAL)
        self.search_button.config(state=tk.NORMAL)
        self.clear_search_button.config(state=tk.NORMAL)
        
        self.is_uploading = False
    def end_remove_file(self, show_message: str = None, errormode: bool = False):
        # Remove finished, clear flags
        self.is_removing = False
        if show_message and not errormode:
            messagebox.showinfo("GanShared", show_message)
        if show_message and errormode:
            messagebox.showerror("GanShared", show_message)

        self.start_show_shared_file_information()
    
    def begin_remove_file(self):
        self.disconnect_button.config(state=tk.DISABLED)
        self.upload_button.config(state=tk.DISABLED)
        self.search_entry.config(state=tk.DISABLED)
        self.search_button.config(state=tk.DISABLED)
        self.clear_search_button.config(state=tk.DISABLED)
        self.refresh_button.config(state=tk.DISABLED)
        self.file_tree_view.unbind("<Button-3>")
        self.file_tree_view.unbind("<Double-Button-1>")
        self.file_tree_view.drop_target_register(DND_FILES)
        self.file_tree_view.dnd_bind('<<Drop>>', self.pass_drop_event)
        self.config(cursor="watch")
        # Mark as removing
        self.is_removing = True
        
    def not_meet_remove_file_requirements(self):
        self.config(cursor="arrow")
        self.file_tree_view.bind("<Button-3>", self.right_click_event)
        self.file_tree_view.bind("<Double-Button-1>", self.double_left_click_event)
        self.file_tree_view.drop_target_register(DND_FILES)
        self.file_tree_view.dnd_bind('<<Drop>>', self.drop_event)
        self.refresh_button.config(state=tk.NORMAL)
        self.upload_button.config(state=tk.NORMAL)
        self.disconnect_button.config(state=tk.NORMAL)
        self.search_entry.config(state=tk.NORMAL)
        self.search_button.config(state=tk.NORMAL)
        self.clear_search_button.config(state=tk.NORMAL)
        
        # Remove finished/canceled
        self.is_removing = False
    
    def begin_download_file(self):
        self.disconnect_button.config(state=tk.DISABLED)
        self.upload_button.config(state=tk.DISABLED)
        self.refresh_button.config(state=tk.DISABLED)
        self.search_entry.config(state=tk.DISABLED)
        self.search_button.config(state=tk.DISABLED)
        self.clear_search_button.config(state=tk.DISABLED)
        # Mark as downloading
        self.is_downloading = True

    def not_meet_download_file_requirements(self):
        self.disconnect_button.config(state=tk.NORMAL)
        self.upload_button.config(state=tk.NORMAL)
        self.refresh_button.config(state=tk.NORMAL)
        self.search_entry.config(state=tk.NORMAL)
        self.search_button.config(state=tk.NORMAL)
        self.clear_search_button.config(state=tk.NORMAL)
        # Download finished/canceled
        self.is_downloading = False
    
    def end_upload_file(self, show_message: str = None, errormode: bool = False):
        # Upload finished, clear flags
        self.is_uploading = False
        try:
            self.upload_progress_window.destroy()
        except:
            pass

        if show_message and not errormode:
            messagebox.showinfo("GanShared", show_message)
            # Trigger refresh (end_refresh will restore UI based on operation flags)
            self.start_show_shared_file_information()

        if show_message and errormode:
            messagebox.showerror("GanShared", show_message)
            self.not_meet_upload_file_requirements()
    
    def end_download_file(self, show_message: str, errormode: bool = False):
        # Download finished, clear flags
        self.is_downloading = False
        try:
            self.download_progress_window.destroy()
        except:
            pass

        if show_message and not errormode:
            messagebox.showinfo("GanShared", show_message)
            self.start_show_shared_file_information()

        if show_message and errormode:
            messagebox.showerror("GanShared", show_message)
            self.not_meet_download_file_requirements()

    def start_disconnect(self):
        self.close_connect("Disconnected successful")  
    
    def begin_refresh(self):
        self.is_refreshing = True
        self.config(cursor="watch")
        self.refresh_button.config(state=tk.DISABLED)
        self.upload_button.config(state=tk.DISABLED)
        self.disconnect_button.config(state=tk.DISABLED)
        self.file_tree_view.unbind("<Button-3>")      
        self.file_tree_view.unbind("<Double-Button-1>")    
        self.file_tree_view.drop_target_register(DND_FILES)
        self.file_tree_view.dnd_bind('<<Drop>>', self.pass_drop_event)
        self.search_entry.config(state=tk.DISABLED)
        self.search_button.config(state=tk.DISABLED)
        self.clear_search_button.config(state=tk.DISABLED)
        
    def end_refresh(self):
        self.is_refreshing = False
        # Only restore bindings and enable buttons when no upload/download/remove operation is in progress

        if not self.is_removing:
            self.config(cursor="arrow")
            self.file_tree_view.bind("<Button-3>", self.right_click_event)
            self.file_tree_view.bind("<Double-Button-1>", self.double_left_click_event)
            self.file_tree_view.drop_target_register(DND_FILES)
            self.file_tree_view.dnd_bind('<<Drop>>', self.drop_event)
            if not (self.is_uploading or self.is_downloading):
                self.refresh_button.config(state=tk.NORMAL)
                self.upload_button.config(state=tk.NORMAL)
                self.disconnect_button.config(state=tk.NORMAL)
                self.search_entry.config(state=tk.NORMAL)
                self.search_button.config(state=tk.NORMAL)
                self.clear_search_button.config(state=tk.NORMAL)
        # Always update filtered list content
        self.filter_file_list(True)
    
    def error_end_refresh(self):
        self.is_refreshing = False
        self.file_tree_view.delete(*self.file_tree_view.get_children())

        # Only restore UI when no upload/download/remove operation is in progress
        if not (self.is_uploading or self.is_downloading or self.is_removing):
            self.config(cursor="arrow")
            self.file_tree_view.bind("<Button-3>", self.right_click_event)
            self.file_tree_view.bind("<Double-Button-1>", self.double_left_click_event)
            self.file_tree_view.drop_target_register(DND_FILES)
            self.file_tree_view.dnd_bind('<<Drop>>', self.drop_event)
            self.refresh_button.config(state=tk.NORMAL)
            self.upload_button.config(state=tk.NORMAL)
            self.disconnect_button.config(state=tk.NORMAL)
    
class AppUpdateChildUI:
    def update_upload_progress(self, percent: float):
        if hasattr(self, 'upload_progress_var') and hasattr(self, 'upload_progress_label'):
            self.upload_progress_var.set(percent)
            self.upload_progress_label.config(text=f"{percent:.1f}%")
    
    def update_show_upload_progress(self, title: str, filename: str, filesize: str):
        self.upload_progress_window.title(f"Uploading {title}")
        if len(filename) < 35:
            self.upload_showfilename.config(text=f"Uploading: {filename}")
        else:
            self.upload_showfilename.config(text=f"Uploading: {filename[0:35]}...")
        
        self.upload_progress_var.set(0)
        self.upload_size_label.config(text=f"Size: {self.format_filesize(filesize)}")
        
        self.upload_progress_window.update_idletasks()
    
    def update_download_progress(self, percent: int):
        if hasattr(self, 'download_progress_var') and hasattr(self, 'download_progress_label'):
            self.download_progress_var.set(percent)
            self.download_progress_label.config(text=f"{percent:.1f}%")
    
class UploadEvent:
    def start_upload_file(self):
        self.begin_upload_file()
        
        all_upload_filepath = filedialog.askopenfilenames(filetypes=[("All files", "*.*")], initialdir=os.path.join(os.path.expanduser("~"), "Desktop"), title="Choose file to upload")
        
        if not all_upload_filepath: 
            self.not_meet_upload_file_requirements()
            return

        for file in all_upload_filepath:
            if os.path.getsize(file) == 0:
                messagebox.showinfo("GanShared", f"{os.path.basename(file)}: Cannot send an empty file or No permission to access")
                self.not_meet_upload_file_requirements()
                return
            
            if os.path.getsize(file) > self.upload_max_size: 
                messagebox.showinfo("GanShared", f"{os.path.basename(file)}:Cannot upload files larger than {self.format_filesize(self.upload_max_size)}")
                self.not_meet_upload_file_requirements()
                return
        
        
        # Initialize cancel event
        self.upload_cancel_event = threading.Event()

        upload_file_thread = threading.Thread(target=self.upload_file, args=(all_upload_filepath, ))
        upload_file_thread.daemon = True 
        upload_file_thread.start()

    def upload_send_file(self, all_filepath: tuple[str], upload_sock: socket.socket) -> int:
        total_files = len(all_filepath)
        self.after_idle(self.show_upload_progress, 
            f"File 1/{total_files}: {os.path.basename(all_filepath[0])}", 
            os.path.basename(all_filepath[0]),
            os.path.getsize(all_filepath[0]))
            
        for index, filepath in enumerate(all_filepath):
            filesize = os.path.getsize(filepath)            
                
            request = {
                "command":"[send_file]", 
                "filename":f"{os.path.basename(filepath)}",
                "username":self.username,
                "filesize":str(filesize),
                "chunk":self.upload_chunk
            }
                
            upload_sock.sendall(json.dumps(request).encode())
                
            response = upload_sock.recv(64)
                
            if response == b"NODISKSPACE":
                raise ConnectionError("Server no disk space")
                
            if response != b"READY":
                raise ConnectionError("Server not ready")
                
            # Check if upload canceled
            if hasattr(self, 'upload_cancel_event') and self.upload_cancel_event.is_set():
                raise Exception("Upload canceled")

            sent = 0
            
            with open(filepath, "rb") as f:
                while True:
                    chunk = f.read(self.upload_chunk)
                    if not chunk:
                        break
                    
                    # Check if upload canceled
                    if hasattr(self, 'upload_cancel_event') and self.upload_cancel_event.is_set():
                        raise Exception("Upload canceled")

                    # Use sendall to ensure the full buffer is sent
                    upload_sock.sendall(chunk)
                    sent += len(chunk)
                        
                    # Update progress
                    progress = (sent / filesize) * 100
                    self.after_idle(self.update_upload_progress, progress)
                        
                f.close()
                    
                self.after_idle(self.update_upload_progress, 100)
                    
                if index < total_files - 1:  # If it is not the last file, update the progress window
                    self.after_idle(self.update_show_upload_progress, 
                    f"File {index+2}/{total_files}: {os.path.basename(all_filepath[index+1])}", 
                    os.path.basename(all_filepath[index+1]),
                    os.path.getsize(all_filepath[index+1]))

        return total_files

    def upload_file(self, all_filepath: tuple[str]):
        try:
            _upload_sock = socket.socket()
            _upload_sock.settimeout(300)
            _upload_sock.connect((self.ip_address, self.port))
            
            upload_sock = self.context.wrap_socket(_upload_sock, server_hostname=self.ip_address)
            
            if self.userdata_json["server_data"][self.ip_address]["key"]:
                upload_sock.recv(64) 
                
                upload_sock.sendall(
                    json.dumps({
                        "do": "operation", 
                        "key": hashlib.sha256(self.userdata_json["server_data"][self.ip_address]["key"].encode()).hexdigest()
                    }).encode()
                )
                
                upload_sock.recv(64)
            
            total_files = self.upload_send_file(all_filepath, upload_sock)
                
            if total_files == 1: 
                self.after_idle(self.end_upload_file, f"Upload: {os.path.basename(all_filepath[0])}")
                return
                
            self.after_idle(self.end_upload_file, f"Upload: {total_files} files")
            
        except (ConnectionResetError, TimeoutError, AttributeError) as e:
            try:
                self.after_idle(self.upload_progress_window.destroy)
            except:
                pass
            
            self.after_idle(self.end_upload_file)
            
            self.after_idle(self.close_connect, "Server connection interrupted", True)
            return
        
        except Exception as e:
            try:
                self.after_idle(self.upload_progress_window.destroy)
            except:
                pass
            
            if str(e) == "Upload canceled":
                self.after_idle(self.end_upload_file, "Upload canceled")
                return

            self.after_idle(self.end_upload_file, f"Upload failed\n{e}", True)
            return
        
        finally:
            try:
                upload_sock.close()
            except:
                pass
        
    def cancel_upload(self):
        self.upload_cancel_event.set()
        self.upload_cancel_button.config(state=tk.DISABLED)

class DownloadEvent:
    def cancel_download(self):
        self.download_cancel_event.set()
        self.download_cancel_button.config(state=tk.DISABLED)
        
    def start_download_file(self):
        self.begin_download_file()
        
        try:
            filename = self.file_tree_view.item(self.file_tree_view.selection()[0])["values"][0]
            format_filesize = self.file_tree_view.item(self.file_tree_view.selection()[0])["values"][3]
        except IndexError:
            self.not_meet_download_file_requirements()
            return
        
        download_filepath = filedialog.asksaveasfilename(filetypes=[("All files", "*.*")], title="Choose file to upload", initialdir=os.path.join(os.path.expanduser("~"), "Desktop"), initialfile=filename)
        
        if not download_filepath:
            self.not_meet_download_file_requirements()
            return
        
        # Initialize cancel event
        self.download_cancel_event = threading.Event()

        download_file_thread = threading.Thread(target=self.download_file, args=(filename, format_filesize, download_filepath))
        download_file_thread.daemon = True
        download_file_thread.start()
    
    def download_get_file(self, filename: str, download_sock: socket.socket, download_filepath: str) -> tuple[int, int]:
        request = {
            "command": "[download_file]",
            "filename": filename,
            "chunk" : self.download_chunk
        }
            
        download_sock.sendall(json.dumps(request).encode())
            
        # Receive file size
        size_response = download_sock.recv(1024)
        if not size_response or size_response == b"-1":
            raise ConnectionError("File not found on server")
            
        # Parse the file size returned by the server
        server_filesize = int(size_response.decode())
            
        if not self.check_disk_space(server_filesize):
            try:
                download_sock.sendall(b"EXIT")
                raise ConnectionError("No disk space")
            except:
                raise ConnectionError("No disk space")
                            
            # Send ready signal
        # Check cancellation before sending READY
        if hasattr(self, 'download_cancel_event') and self.download_cancel_event.is_set():
            try:
                download_sock.sendall(b"EXIT")
            except:
                pass
            raise Exception("Download canceled")

        download_sock.sendall(b"READY")
            
        # Receive file
        received = 0
        with open(download_filepath, 'wb') as f:
            while received < server_filesize:
                remaining = server_filesize - received
                chunk_size = min(self.download_chunk, remaining)
                chunk = download_sock.recv(chunk_size)
                if not chunk:
                    break
                # Check cancel request
                if hasattr(self, 'download_cancel_event') and self.download_cancel_event.is_set():
                    try:
                        download_sock.sendall(b"EXIT")
                    except:
                        pass
                    raise Exception("Download canceled")

                f.write(chunk)
                received += len(chunk)
                    
                # Update progress
                progress = (received / server_filesize) * 100
                self.after_idle(self.update_download_progress, progress)
            
            f.close()
        
        return received, server_filesize
      
    def download_file(self, filename: str, format_filesize: str, download_filepath: str):
        try:
            # Show download progress
            self.after_idle(self.show_download_progress, filename, format_filesize)
            
            # Create a new socket connection
            _download_sock = socket.socket()
            _download_sock.settimeout(300)
            _download_sock.connect((self.ip_address, self.port))
            
            download_sock = self.context.wrap_socket(_download_sock, server_hostname=self.ip_address)
            
            if self.userdata_json["server_data"][self.ip_address]["key"]:
                download_sock.recv(64)
                
                download_sock.sendall(
                    json.dumps({
                        "do": "operation",
                        "key": hashlib.sha256(self.userdata_json["server_data"][self.ip_address]["key"].encode()).hexdigest()
                    }).encode())

                download_sock.recv(64)
            
            received, server_filesize = self.download_get_file(filename, download_sock, download_filepath)

            if received == server_filesize:
                self.after_idle(self.end_download_file, f"Download successful: {filename}")
            else:
                raise Exception(f"Incomplete download: {received}/{server_filesize} bytes")
        
        except (ConnectionResetError, TimeoutError, AttributeError) as e:
            if os.path.exists(download_filepath):
                try:
                    os.remove(download_filepath)
                except:
                    pass
                
            try:
                self.after_idle(self.download_progress_window.destroy)
            except:
                pass
        
            self.after_idle(self.error_end_refresh)
            self.after_idle(self.close_connect, "Server connection interrupted")
        
        except Exception as e:
            try:
                self.after_idle(self.download_progress_window.destroy)
            except:
                pass
            
            if os.path.exists(download_filepath):
                try:
                    os.remove(download_filepath)
                except:
                    pass
            # Distinguish cancel operation
            if str(e) == "Download canceled":
                self.after_idle(self.end_download_file, "Download canceled")
                return

            self.after_idle(self.end_download_file, f"Download failed\n{e}", True)  
        finally:
            try:
                download_sock.close()         
            except:
                pass

class RefrehEvent:
    def get_shared_file_information(self) -> (dict | None):
        try:
            
            request = {"command": "[get_shared_file_information]"}
            
            self.sock.sendall(json.dumps(request).encode())
            byteslen = int(self.sock.recv(64).decode())
            
            self.sock.sendall(b"READY")
        
            result = self.recv_exact(self.sock, byteslen).decode()
            
            if result == "":
                return
            
        except (TimeoutError, ConnectionResetError) as e:
            self.after_idle(self.error_end_refresh)
            self.close_connect("Server connection interrupted", True)
        
            return None
        except Exception as e:
            self.after_idle(self.error_end_refresh)
            messagebox.showerror("GanShared", f"{e}")
            
            return None
        
        try:
            return json.loads(result) 
        except Exception as e:
            self.after_idle(self.error_end_refresh)
            messagebox.showerror("GanShared", f"{e}")
            return None
    
    def start_show_shared_file_information(self):
        show_shared_file_information_thread = threading.Thread(target=self.show_shared_file_information)
        show_shared_file_information_thread.daemon = True
        show_shared_file_information_thread.start()

    def show_shared_file_information(self):
        self.after_idle(self.begin_refresh)
        
        shared_file_information = self.get_shared_file_information() 
        if shared_file_information is None:
            return 
        
        all_filename = shared_file_information["all filename"]
        all_file_send_time = shared_file_information["all file send time"]
        all_file_size = shared_file_information["all file size"]
        all_file_send_user = shared_file_information["all file send user"]
        
        self.search_entry.config(values=all_filename)
        
        now_all_filename = []
        
        search_bvar = self.search_var.get()
        
        self.search_var.set("")
        all_items = self.file_tree_view.get_children()
        self.search_var.set(search_bvar)
        self.search_entry.icursor(len(search_bvar))
        
        for item in all_items:
            now_all_filename.append(self.file_tree_view.item(item)["values"][0])

        if not all_filename == now_all_filename:
            missing_in_allfilename = list(set(now_all_filename) - set(all_filename))
            if missing_in_allfilename:
                for missing_index in range(len(missing_in_allfilename)):
                    del_file = self.find_id_by_content(missing_in_allfilename[missing_index])
                    if not del_file:
                        return
                    
                    self.file_tree_view.delete(del_file)

            else:
            
                missing_in_now_allfilename = [item for item in all_filename if item not in now_all_filename]
                
                location = "0"
                if not now_all_filename:
                    location = "end"
                
                for index in missing_in_now_allfilename:
                    item_id = self.file_tree_view.insert("", location, values=(
                        all_filename[all_filename.index(index)], 
                        all_file_send_user[all_filename.index(index)], 
                        all_file_send_time[all_filename.index(index)], 
                        self.format_filesize(all_file_size[all_filename.index(index)]))
                    )
                        
                    # Save original data        
                    self.file_items[item_id] = {
                        "Filename": all_filename[all_filename.index(index)],
                        "Send_user": all_file_send_user[all_filename.index(index)],
                        "Send_time": all_file_send_time[all_filename.index(index)],
                        "Size": self.format_filesize(all_file_size[all_filename.index(index)])
                    }
        
        
        self.after_idle(self.end_refresh)

    def start_auto_refresh(self):
        if self.auto_refresh_id is not None:
            self.after_cancel(self.auto_refresh_id)
        
        # Start a new scheduled task
        if self.refresh_interval == -1:
            return
        
        self.auto_refresh_id = self.after((self.refresh_interval*1000), self.auto_refresh)
    
    def auto_refresh(self):
        if not self.is_connected:
            self.auto_refresh_id = None
            return
        
        if self.refresh_interval == -1:
            return
        
        # Reschedule the next refresh first
        self.auto_refresh_id = self.after((self.refresh_interval*1000), self.auto_refresh)
        
        # If already refreshing, skip this one
        if self.is_refreshing:
            return
        
        # Start refresh
        self.start_show_shared_file_information()

class SearchEvent:
    def filter_file_list(self, refresh=False):
        search_text = re.sub("\n", "", self.search_var.get().lower())
        
        if not search_text and refresh==False:
            self.show_all_files()
            return
        elif not search_text and refresh:
            return
        
        if not refresh:
            # Show all files first
            self.show_all_files()
        
        # Get all items
        all_items = self.file_tree_view.get_children()
        
        show_values = []
        
        for item in all_items:
            filename = self.file_tree_view.item(item)["values"][0]
            send_user = self.file_tree_view.item(item)["values"][1]
            
            # Search in filename and uploader
            if (search_text in filename.lower() or 
                search_text in send_user.lower()):
                show_values.append(filename)
            else:
                # No match, hide
                if not refresh:
                    self.hidden_items.add(item)
                self.file_tree_view.detach(item)
        
        if self.entry_mode.get() == "Predictive search mode":     
            self.search_entry.config(values=show_values)
            
    def clear_search(self):
        self.search_var.set("")
        self.show_all_files()
        self.search_entry.focus()
    
    def sort_treeview(self):
        all_items = list(self.file_tree_view.get_children())
        
        # Reinsert to restore order
        for item_id, item_data in self.file_items.items():
            if item_id in all_items:
                # Detach first
                self.file_tree_view.detach(item_id)
                # Reattach to end
                self.file_tree_view.reattach(item_id, "", "end")
    
    def show_all_files(self):
        if not self.hidden_items:
            return
        
        # Reattach all hidden items at the end
        for item in list(self.hidden_items):
            try:
                self.file_tree_view.reattach(item, "", "end")
            except tk.TclError:
                # If the item has already been deleted, skip it
                pass
        
        # Clear hidden item list
        self.hidden_items.clear()
        
        # Re-sort according to original data order
        self.sort_treeview()
    
    def on_search_change(self, *args):
        if self.enter_search.get() == 0:
            return 
        
        search_text = self.search_var.get().strip()

        if len(search_text) >= 1:  
            self.filter_file_list()         
            
        if len(search_text) == 0:
            self.show_all_files()

    def on_search(self, event=None):
        self.filter_file_list()

class RemoveEvent:
    def remove_file(self, filename: str):
        try:
            request = {
                "command": "[remove_file]",
                "filename": filename
            }
            
            self.sock.sendall(json.dumps(request).encode())
            
            if self.userdata_json["remove_not_message"] == 0:
                self.after_idle(self.end_remove_file, f"Remove: {filename}")
            
            else:
                self.after_idle(self.end_remove_file)
        
        except (TimeoutError, ConnectionResetError) as e:
            self.after_idle(self.end_remove_file)
            self.after_idle(self.close_connect, "Server connection interrupted")
        
        except Exception as e:
            self.after_idle(self.end_remove_file, f"Deletion failed\n{e}", True)
    
    def start_remove_file(self):
        self.begin_remove_file()
        
        try:
            filename = self.file_tree_view.item(self.file_tree_view.selection()[0])["values"][0]
        except IndexError:
            self.not_meet_remove_file_requirements()
            return
        
        if self.userdata_json["remove_not_message"] == 0:
            do = messagebox.askyesno("GanShared", f"Do you want to delete {filename}?")
            
            if not do:
                self.not_meet_remove_file_requirements()
                return
        
        remove_file_thread = threading.Thread(target=self.remove_file, args=(filename, ))
        remove_file_thread.daemon = True
        remove_file_thread.start() 

class OtherEvent:
    def copy_filename(self):
        try:
            self.copy_to_clipboard(self.file_tree_view.item(self.file_tree_view.selection()[0])["values"][0])
        except IndexError:
            pass

class AppMain(
    TkinterDnD.Tk, 
    InitApp, 
    AppCreateTopUI, 
    AppTools, 
    AppNetwork, 
    AppEvent, 
    AppSet, 
    AppUpdateTopUI, 
    AppUpdateChildUI, 
    AppCreateChildUI, 
    UploadEvent, 
    DownloadEvent, 
    RefrehEvent, 
    SearchEvent, 
    RemoveEvent,
    OtherEvent, 
    AppServerManagement, 
    AppHelp
    ):
    def on_closing(self):
        if hasattr(self, 'sock') and self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        
        with open(self.userdata_file, "w", encoding="utf-8") as f:
            json.dump(self.userdata_json, f, indent=4)
            f.close()

        try:   
            self.destroy()
        except Exception:
            pass
        
        sys.exit(0)
        
    def __init__(self):
        super().__init__(className="GanShared")

        self.title("GanShared")
        self.geometry("900x500")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.withdraw()
        
        if not self.init_app():
            self.on_closing()
            return

        self.deiconify()
        self.create_ui()
        
if __name__ == "__main__":   
    if sys.platform not in ("win32", "darwin", "linux"):
        messagebox.showinfo("GanShared", "This platform is not supported")
        sys.exit(1)
    app = AppMain()
    app.mainloop()
