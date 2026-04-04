# GanShared

## Overview
GanShared is a cross-platform, lightweight file sharing application. It supports secure, encrypted file transfers, server management, and a user-friendly graphical interface.

*   **Current Version**: 1.2.11.1release
*   **Author**: youngyyds
*   **License**: MIT
*   **Repository**: https://github.com/youngyyds/GanShared
*   **Releases**: https://github.com/youngyyds/GanShared/releases

## Features

### Client (`main.py`)
The client provides a graphical interface for users to connect to servers and manage files.

*   **Connection Management**
    *   Connect/Disconnect from a server with configurable IP, username, and password.
    *   Key-based authentication (prompted if required by the server).
    *   Real-time connection status display.

*   **File Operations**
    *   **Upload**: Supports multiple files, large file transfers, drag-and-drop, and cancellation during upload. Checks local disk space before uploading.
    *   **Download**: Download via double-click or right-click context menu.
    *   **Delete**: Delete files with an optional confirmation prompt.
    *   **Search**: Real-time file search with "All files" or "Predictive search" modes.
    *   Copy filename via the right-click menu.

*   **Configuration & Customization**
    *   JSON-based configuration file (userdata.json).
    *   Editable settings: username, server IP, chunk size per transfer, auto-refresh interval, search mode, and deletion prompts.
    *   Handles configuration file corruption.
    *   Prompts for missing IP/username on first launch.

*   **Server & Key Management**
    *   Manage multiple servers (add, delete, edit, set default).
    *   Manage keys for different servers (add, delete, view).

*   **User Experience**
    *   Clear error messages and prompts.
    *   Auto-refresh for the file list.
    *   Right-click context menus.

*   **Security**
    *   Encrypted transmission using SSL/TLS with certificate authentication.

### Server (`server.py`)
The server handles file storage, client authentication, and request processing. It can be configured via a graphical admin interface.

*   **Core Server**
    *   Listens for client connections on a specified port.
    *   Handles client commands: upload, download, delete, list files.
    *   Manages concurrent client connections using threads.

*   **Configuration & Management (GUI)**
    *   Graphical interface to set the server key (optional) and the maximum number of stored files.
    *   Configuration saved to server_config.json.

*   **File & Storage Management**
    *   Stores files and uploader metadata separately.
    *   Implements file cleanup based on a configurable maximum file limit (max_stored_files). Supports -1 for no limit.
    *   Uses unique filenames to avoid overwrites.

*   **Security**
    *   Optional key-based authentication for clients.
    *   Encrypted communication using SSL/TLS.
    *   Prevents duplicate logins from the same IP when a key is set.

*   **Logging**
    *   Logs server activity and errors to server.log.

## Planned Features (Client)
The following features are planned for future releases of the client:
1.  File preview (images, text, etc.)
2.  File chunking & resumable upload/download
3.  Advanced permission management (Owner, Administrator, Advanced User levels)
4.  Advanced search (filter by size, uploader, etc.)
5.  Folder upload
6.  Shareable download links
7.  Dark theme
8.  Multi-language support

### Configuration Files
*   **Client**: userdata.json (Stored in OS-specific application data folder, e.g., %LOCALAPPDATA%\GanShared\ on Windows).
*   **Server**: server_config.json (Also stored in OS-specific application data folder).

---
*This application is under active development. Expect regular updates and new features.*
