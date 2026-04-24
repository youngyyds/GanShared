# Copyright (c) 2026 youngyyds
# Licensed under the MIT License. See LICENSE file for details

import socket
import threading
import os
import getpass
import time
import json
from typing import Any
import math
import hashlib
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import logging
from logging.handlers import RotatingFileHandler
import ssl
import platform
import sys

__version__ = "1.2.11.1"

class AppInit:        
    def init_app(self, loadssl: bool = True):
        self.sock = socket.socket()
        self.port = 45622
        self.listen = 120
        self.system_username = getpass.getuser()
        if sys.platform == "win32":
            self.data_folder_path = os.path.join(os.path.expanduser("~"), "AppData", "Local", "GanShared")
        elif sys.platform == "linux":
            self.data_folder_path = os.path.join(os.path.expanduser("~"), ".local", "share", "GanShared")
        elif sys.platform == "darwin":
            self.data_folder_path = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "GanShared")
        # Max stored files can be configured via GUI or server_config.json, default 512
        self.max_stored_files = 512
        self.save_files_dir = os.path.join(self.data_folder_path, "save_files")
        self.files_user_dir = os.path.join(self.data_folder_path, "files_user")
        self.key = None
        # server config file path (writable by GUI)
        self.server_config_path = os.path.join(self.data_folder_path, "server_config.json")
        if getattr(sys, 'frozen', False):
            self.core_dir = os.path.join(os.path.dirname(sys.executable), "main")
        else:
            self.core_dir = os.path.dirname(os.path.abspath(__file__))
        self.all_ipaddress = []
        
        os.chdir(self.data_folder_path)
        if not os.path.exists(self.data_folder_path):
            os.makedirs(self.data_folder_path)
        if not os.path.exists(self.save_files_dir):
            os.makedirs(self.save_files_dir)
        if not os.path.exists(self.files_user_dir):
            os.makedirs(self.files_user_dir)

        if loadssl:
            self.context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            
            self.context.verify_mode = ssl.CERT_REQUIRED
            self.context.check_hostname = False

            try:
                self.context.load_verify_locations(cafile=os.path.join(self.core_dir, "ca.crt"))
                self.context.load_cert_chain(
                    certfile=os.path.join(self.core_dir, "server.crt"), 
                    keyfile=os.path.join(self.core_dir, "server.key"), 
                    password=self.get_password()
                )
            except Exception as e:
                messagebox.showerror(
                    "Error", 
                    "Failed to load SSL certificate and key."\
                    f"\n{e}\n"\
                    f"\nPlease check if the core directory '{self.core_dir}' is writable by the current user."\
                )
                sys.exit(1)
                
        # configure logging to file inside data folder
        try:
            logger = logging.getLogger('GanSharedServer')
            logger.setLevel(logging.INFO)
            log_path = os.path.join(self.data_folder_path, 'server.log')
            handler = RotatingFileHandler(log_path, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
            handler.setFormatter(formatter)
            if not logger.handlers:
                logger.addHandler(handler)
            self.logger = logger
            self.logger.info('Logger initialized')
        except Exception as e:
            # best-effort logging; continue
            messagebox.showerror(
                "Error", 
                "Failed to initialize logger"\
                f"\n{e}"\
                f"\nPlease check if the data folder {self.data_folder_path} is writable by the current user."\
            )
            sys.exit(1)

        # Ensure server_config.json exists; migrate old key.txt if present
        try:
            if not os.path.exists(self.server_config_path):
                migrated_key = None

                self.cfg = {"max_stored_files": self.max_stored_files, "key": migrated_key}
                
                try:
                    with open(self.server_config_path, "w", encoding="utf-8") as cf:
                        json.dump(self.cfg, cf)
                    try:
                        self.logger.info('Created default server_config.json')
                    except Exception:
                        pass
                except Exception:
                    try:
                        self.logger.exception('Failed to create server_config.json')
                    except Exception:
                        pass

            # If server_config.json exists, try loading it to override defaults
            else:
                with open(self.server_config_path, "r", encoding="utf-8") as cfgf:
                    self.cfg = json.load(cfgf)
                if isinstance(self.cfg, dict):
                    if "max_stored_files" in self.cfg:
                        try:
                            val = int(self.cfg.get("max_stored_files", self.max_stored_files))
                            # allow -1 (no limit) or positive integers up to 65565
                            if val == -1 or (1 <= val <= 65565):
                                self.max_stored_files = val
                            elif val > 65565:
                                self.max_stored_files = 65565
                        except Exception:
                            pass
                    # key is kept inside server_config.json; no separate keyfile used
        except Exception:
            pass

class ServerAdminGUI(tk.Tk, AppInit):
    def __init__(self):
        super().__init__()
        self.title("GanShared Server Admin")
        self.resizable(False, False)

        self.init_app(False)
        
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        frm = ttk.Frame(self, padding=12)
        frm.grid(row=0, column=0)

        ttk.Label(frm, text="Max stored files:").grid(row=0, column=0, sticky=tk.W)
        self.max_files_var = tk.IntVar(value=self.cfg.get("max_stored_files", 512))
        # allow -1 to mean "no limit"; enforce upper bound 65565
        self.max_files_spin = ttk.Spinbox(frm, from_=-1, to=65565, textvariable=self.max_files_var, width=10)
        self.max_files_spin.grid(row=0, column=1, sticky=tk.W)

        ttk.Label(frm, text="Server key (leave empty to disable):").grid(row=1, column=0, sticky=tk.W, pady=(8,0))
        self.key_var = tk.StringVar()
        self.key_entry = ttk.Entry(frm, textvariable=self.key_var, width=40)
        self.key_var.set(self.cfg.get("key", "") if self.cfg.get("key", None) is not None else "")
        self.key_entry.grid(row=1, column=1, sticky=tk.W, pady=(8,0))

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(12,0))
        
        self.run_btn = ttk.Button(btn_frame, text="Run the server", 
                                  command=self.run_server, takefocus=False)
        self.run_btn.grid(row=0, column=0, padx=6)
        save_btn = ttk.Button(btn_frame, text="Save", command=self._save, takefocus=False)
        save_btn.grid(row=0, column=1, padx=6)
        exit_btn = ttk.Button(btn_frame, text="Exit", command=self.destroy, takefocus=False)
        exit_btn.grid(row=0, column=2, padx=6)
        
    def _load_values(self):
        # load max files from server_config.json if exists
        try:
            if isinstance(self.cfg, dict) and "max_stored_files" in self.cfg:
                try:
                    val = int(self.cfg.get("max_stored_files", 512))
                    # cap to allowed range (-1 or 1..65565)
                    if val == -1:
                        self.max_files_var.set(-1)
                    elif 1 <= val <= 65565:
                        self.max_files_var.set(val)
                    elif val > 65565:
                        self.max_files_var.set(65565)
                except Exception:
                    pass
        except Exception:
            pass

    def _log_gui_action(self, msg: str, level: str = "info"):
        try:
            logger = logging.getLogger('GanSharedServer')
            if level == "info":
                logger.info(msg)
            elif level == "warning":
                logger.warning(msg)
            elif level == "error":
                logger.error(msg)
            else:
                logger.debug(msg)
        except Exception:
            pass

        # load key from server_config.json if exists
        try:
            if os.path.exists(self.server_config_path):
                k = self.cfg.get("key") if isinstance(self.cfg, dict) else None
                if k and k != "None":
                    self.key_var.set(str(k))
                else:
                    self.key_var.set("")
        except Exception:
            pass
    
    def _save(self, show_message=True) -> bool:
        # Validate inputs
        raw_max = None
        try:
            raw_max = int(self.max_files_var.get())
        except Exception:
            messagebox.showerror("Error", "Max stored files must be an integer (use -1 for no limit)")
            return False

        max_files = raw_max
        key = self.key_var.get()

        # validate max_files: allow -1 or positive integer up to 65565
        if not (max_files == -1 or (max_files > 0 and max_files <= 65565)):
            messagebox.showinfo("GanShared", "Max stored files must be -1 (no limit) or a positive integer up to 65565")
            return False

        # validate key length when provided
        if key != "":
            if not (5 <= len(key) <= 30):
                messagebox.showinfo("GanShared", "Key length must be between 5 and 30 characters")
                return False
        else:
            do = messagebox.askokcancel("GanShared", "Key will be disabled. Your server will not require any authentication. Are you sure?", icon="warning", default="cancel")
            if not do:
                return False
            

        # write server_config.json
        try:
            cfg = {"max_stored_files": int(max_files)}
            # store key (None if empty)
            if key == "":
                cfg["key"] = None
            else:
                cfg["key"] = key
                
            with open(self.server_config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to write server_config.json:\n{e}")
            return False

        # key is stored inside server_config.json (already written above)
        if show_message:
            messagebox.showinfo("Saved", "Configuration saved successfully.")
        self._log_gui_action(f"Saved config: max_stored_files={max_files}, key_set={bool(key)}")
        
        return True

    def run_server(self):
        # Save current configuration before starting the server
        try:
            if not self._save(False):
                return
        except Exception:
            pass

        if getattr(self, '_server_thread_started', False):
            messagebox.showinfo("GanShared", "Server is already running")
            return

        try:
            try:
                self.run_btn.config(state=tk.DISABLED)
            except Exception:
                pass
            messagebox.showinfo("GanShared", "Server started")
            self._log_gui_action("Server started by GUI")
            self.destroy()
            
            AppMain()
        except Exception as e:
            logging.getLogger('GanSharedServer').exception("Failed to start server from GUI")
            messagebox.showerror("Error", f"Failed to start server:\n{e}")

class AppTools:
    def get_password(self) -> str:
        import secret
        
        server_cert = secret.decrypt_aes(secret.server_cert, hashlib.md5(platform.processor().encode()).hexdigest())
        
        return server_cert
    
    def check_disk_space(self, required_bytes: int) -> bool:
        # If max_stored_files == -1, skip disk space checking
        try:
            if getattr(self, 'max_stored_files', None) == -1:
                return True
            import shutil
            total, used, free = shutil.disk_usage(self.data_folder_path)
            return free >= required_bytes
        except Exception as e:
            try:
                logging.getLogger('GanSharedServer').exception('Error checking disk space')
            except Exception:
                pass
            return False

    def recv_exact(self, sock: socket.socket, n: int) -> bytes:
        data = bytearray()
        while len(data) < n:
            part = sock.recv(n - len(data))
            if not part:
                raise ConnectionError("Socket closed during recv_exact")
            data.extend(part)
        return bytes(data)
    
    def cleanup_old_files(self, max_files: int = None):
        try:
            if max_files is None:
                max_files = self.max_stored_files

            # If max_stored_files == -1, do not perform cleanup
            if getattr(self, 'max_stored_files', None) == -1:
                return
            
            if not os.path.exists(self.save_files_dir):
                return
            
            # Count only final files (exclude temporary upload suffix .shared_part)
            all_files = [fn for fn in os.listdir(self.save_files_dir) if not fn.endswith('.shared_part')]
            current_count = len(all_files)

            if current_count <= max_files:
                return

            files_to_remove = current_count - max_files
            oldest_files = self.get_oldest_files(files_to_remove)
            
            for filename in oldest_files:
                try:
                    # Delete main file
                    filepath = os.path.join(self.save_files_dir, filename)
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    
                    # Delete user info file
                    user_file = os.path.join(self.files_user_dir, filename)
                    if os.path.exists(user_file):
                        os.remove(user_file)
                except Exception:
                    pass
            
        except Exception:
            pass
    
    def get_oldest_files(self, limit: int = 1):
        try:
            if not os.path.exists(self.save_files_dir):
                return []
            
            files_with_time = []
            for filename in os.listdir(self.save_files_dir):
                # Ignore temporary upload files
                if filename.endswith('.shared_part'):
                    continue
                filepath = os.path.join(self.save_files_dir, filename)
                if os.path.isfile(filepath):
                    try:
                        create_time = os.path.getctime(filepath)
                        files_with_time.append((filename, create_time))
                    except:
                        continue
        
            files_with_time.sort(key=lambda x: x[1])
            return [file[0] for file in files_with_time[:limit]]
            
        except Exception as e:
            try:
                logging.getLogger('GanSharedServer').exception('Error getting oldest files')
            except Exception:
                pass
            return []
    
    def get_unique_filename(self, filename: str) -> str:
        filepath = os.path.join(self.save_files_dir, filename)
        if not os.path.exists(filepath):
            return filename
        
        base, ext = os.path.splitext(filename)
        counter = 1
        
        while True:
            new_filename = f"{base}_{counter}{ext}"
            new_filepath = os.path.join(self.save_files_dir, new_filename)
            if not os.path.exists(new_filepath):
                return new_filename
            counter += 1
    
    def verifed_user(self, usersock: socket.socket, ip_address: str) -> bool:
        if self.get_key() is None:
            return True
        
        # If a key exists, verification is required
        try:
            key = self.get_key()
            usersock.sendall(b"KEY_REQUIRED")

            return_msg = json.loads(usersock.recv(1024).decode())
            
            if not isinstance(return_msg, dict):
                raise ValueError("Invalid return message format")
            
            return_msg_do = return_msg.get("do")
            return_msg_key = return_msg.get("key")
            
            if not (hashlib.sha256(key.encode()).hexdigest() == return_msg_key):
                usersock.sendall(b"PWD_ERROR")
                return False
            
            if return_msg_do == "auth":
                if ip_address in self.all_ipaddress:
                    usersock.sendall(b"DUPLICATE_IP")
                    return False
            
            elif return_msg_do == "operation":
                pass
            else:
                raise ValueError("Invalid return message 'do' field")

            return True
            
        except Exception as e:
            try:
                usersock.sendall(b"AUTH_FAILED")
            except Exception:
                pass
            return False
    
    def get_key(self) -> str:
        try:
            if os.path.exists(self.server_config_path):
                with open(self.server_config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if isinstance(cfg, dict):
                    k = cfg.get("key")
                    if k is None or str(k) == "None":
                        return None
                    return str(k)
        except Exception:
            pass
        return None

class AppMain(
    AppInit,
    AppTools
):
  
    def user_get_shared_file_information(self, usersock: socket.socket):
        try:
            # Return only final files (ignore .shared_part temp uploads)
            filenames = [fn for fn in os.listdir(self.save_files_dir) if not fn.endswith('.shared_part')]
            file_info_list = []
            
            for filename in filenames:
                filepath = os.path.join(self.save_files_dir, filename)
                user_file = os.path.join(self.files_user_dir, filename)
                
                if not os.path.exists(filepath):
                    continue
                
                try:
                    # Get file information
                    create_time = os.path.getctime(filepath)
                    file_size = os.path.getsize(filepath)
                    
                    # Get uploader information
                    if os.path.exists(user_file):
                        with open(user_file, 'r', encoding="utf-8") as f:
                            uploader = f.read().strip()
                    else:
                        uploader = "Unknown"
                    
                    file_info_list.append({
                        "filename": filename,
                        "create_time": create_time,
                        "size": file_size,
                        "uploader": uploader
                    })
                    
                except Exception as e:
                    try:
                        logging.getLogger('GanSharedServer').exception(f'Error getting info for {filename}')
                    except Exception:
                        pass
                    continue
            
            # Sort by creation time descending (newest first)
            file_info_list.sort(key=lambda x: x["create_time"], reverse=True)
            
            # Extract the sorted list
            sorted_filenames = [info["filename"] for info in file_info_list]
            sorted_send_times = [time.strftime("%Y-%m-%d %H:%M", 
                                            time.localtime(info["create_time"])) 
                            for info in file_info_list]
            sorted_sizes = [info["size"] for info in file_info_list]
            sorted_uploaders = [info["uploader"] for info in file_info_list]
            
            send_information = {
                "all filename": sorted_filenames,
                "all file send time": sorted_send_times,
                "all file size": sorted_sizes,
                "all file send user": sorted_uploaders
            }            
            send_bytes = json.dumps(send_information).encode()
            send_information_bytes = len(send_bytes)

            usersock.sendall(str(send_information_bytes).encode())

            resp = usersock.recv(64)
            if resp != b"READY":
                raise ConnectionError("Client not READY")

            usersock.sendall(send_bytes)
            
        except Exception as e:
            try:
                logging.getLogger('GanSharedServer').exception('Error getting file information')
            except Exception:
                pass

    def user_upload_shared_file(self, usersock: socket.socket, message: str):
        try:
            filename = os.path.basename(message["filename"])  # Prevent path traversal
            
            filesize = int(message["filesize"])
            # Generate a unique filename
            filename = self.get_unique_filename(filename)
            filepath = os.path.join(self.save_files_dir, filename)
            # Temporarily write to .shared_part suffix, then rename to final file
            temp_filepath = filepath + ".shared_part"
            user_info_path = os.path.join(self.files_user_dir, filename)
            
            # If configured as -1, skip disk checking and cleanup
            if getattr(self, 'max_stored_files', None) != -1:
                if not self.check_disk_space(math.ceil(float(filesize))):
                    usersock.send(b"NODISKSPACE")
                    return

                # Clean up old files to make room for the new file
                self.cleanup_old_files(self.max_stored_files - 1)

            usersock.send(b"READY")

            received = 0
            # Write temporary file
            with open(temp_filepath, "wb") as f:
                while filesize > received:
                    remaining = filesize - received
                    chunk_size = min(message["chunk"], remaining)
                    try:
                        chunk = self.recv_exact(usersock, chunk_size)
                    except ConnectionError:
                        break
                    f.write(chunk)
                    received += len(chunk)

            # If the received data is incomplete, delete the temp file and return (client may have canceled)
            if received < filesize:
                try:
                    if os.path.exists(temp_filepath):
                        os.remove(temp_filepath)
                except Exception:
                    pass
                return

            # Rename temp file to final file and save uploader info
            try:
                os.replace(temp_filepath, filepath)
                with open(user_info_path, "w", encoding="utf-8") as f:
                    f.write(message["username"])
            except Exception:
                try:
                    if os.path.exists(temp_filepath):
                        os.remove(temp_filepath)
                    if os.path.exists(filepath):
                        os.remove(filepath)
                except Exception:
                    pass
                return
    
        except Exception as e:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                if os.path.exists(user_info_path):
                    os.remove(user_info_path)
            except:
                pass
            
            try:
                logging.getLogger('GanSharedServer').exception(f'Upload error: {e}')
            except Exception:
                pass

    def user_download_shared_file(self, usersock: socket.socket, message: str):
        try:
            filename = os.path.basename(message["filename"])  # Prevent path traversal
            filepath = os.path.join(self.save_files_dir, filename)  # Use the correct path
            
            if not os.path.exists(filepath):
                usersock.send(b"-1")  # File does not exist
                raise
            
            # Get file size
            file_size = os.path.getsize(filepath)
            
            # Send file size
            usersock.sendall(str(file_size).encode())
            
            # Wait for client readiness
            response = usersock.recv(64)
            if response == b"EXIT":
                return
            
            if response != b"READY":
                raise
            
            # Send file
            with open(filepath, "rb") as f:
                while True:
                    data = f.read(message["chunk"])
                    if not data:
                        break
                    # Use sendall to ensure full data is sent
                    usersock.sendall(data)
            
        except Exception as e:
            try:
                logging.getLogger('GanSharedServer').exception(f'Download error: {e}')
            except Exception:
                pass
            
    def user_remove_shared_file(self, message: Any):
        try:
            filename = os.path.basename(message["filename"])  # Prevent path traversal
            file_path = os.path.join(self.save_files_dir, filename)
            temp_file_path = file_path + ".shared_part"
            user_path = os.path.join(self.files_user_dir, filename)             

            # Delete final file and any temporary file
            if os.path.exists(file_path):
                os.remove(file_path)
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            if os.path.exists(user_path):  # Check the correct path
                os.remove(user_path)
            
        except Exception as e:
            try:
                logging.getLogger('GanSharedServer').exception(f'Delete shared file error: {e}')
            except Exception:
                pass
    
    def user(self, usersock: socket.socket, ip_address: str):
        try:
            if not self.verifed_user(usersock, ip_address):                
                usersock.close()
                return 
            
            usersock.send(b"VERIFIED")
            
            self.all_ipaddress.append(ip_address)
            
            self.logger.info(f"User {ip_address} connected")
        except Exception as e:
            self.logger.info(f"Error: {e}")
            return 
        
        try:
            usersock.settimeout(1800)
            while True:
                message = usersock.recv(8192).decode()
                
                message = json.loads(message)
                
                if message["command"] == "[check_owner]":
                    self.logger.info(f"User {ip_address} is checking owner")
                    # Verify user ownership with encrypted key transmission
                    
                    key = message.get("key")
                    
                    if key is None or str(key) == "None":
                        usersock.sendall(b"NO_KEY")
                        continue
                    
                if message["command"] == "[get_shared_file_information]":
                    self.logger.info(f"User {ip_address} requested file information")
                    self.user_get_shared_file_information(usersock)
                    continue

                if message["command"] == "[send_file]":
                    self.logger.info(f"User {ip_address} is uploading file: {message.get('filename', 'Unknown')}")
                    self.user_upload_shared_file(usersock, message)
                    continue
            
                if message["command"] == "[download_file]":
                    self.logger.info(f"User {ip_address} is downloading file: {message.get('filename', 'Unknown')}")
                    self.user_download_shared_file(usersock, message)
                    continue
                
                if message["command"] == "[remove_file]":
                    self.logger.info(f"User {ip_address} is deleting file: {message.get('filename', 'Unknown')}")
                    self.user_remove_shared_file(message)
                    continue
                
        except Exception as e: 
            self.logger.info(f"User {ip_address} disconnected")
            usersock.close()
            self.all_ipaddress.pop(self.all_ipaddress.index(ip_address))
            return
                  
    def __init__(self):
        self.init_app()
        
        self.sock.bind(("", self.port))
        self.sock.listen(0)
        
        while True:
            try:
                _usersock, address = self.sock.accept()
                
                usersock = self.context.wrap_socket(_usersock, server_side=True) 
                
                userthread = threading.Thread(target=self.user, args=(usersock, address[0], ))
                userthread.daemon = True
                userthread.start()
            except Exception as e:
                self.logger.error(f"Error accepting connection: {e}")
                
                try:
                    usersock.close()
                except Exception:
                    pass

if __name__ == "__main__":
    if sys.platform not in ("win32", "darwin", "linux"):
        messagebox.showinfo("GanShared", "This platform is not supported")
        sys.exit(1)
        
    ServerAdminGUI().mainloop()
