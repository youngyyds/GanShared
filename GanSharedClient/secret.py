# Copyright (c) 2026 youngyyds
# Licensed under the MIT License. See LICENSE file for details

import Cryptodome.Cipher.AES as AES
import base64
import platform    
import hashlib  

def pad(text):
   while len(text) % 16 != 0:
       text += '\0'
   return text.encode()

def encrypt_aes(text, key):
   aes = AES.new(pad(key), AES.MODE_ECB) 
   encrypted = aes.encrypt(pad(text))
   return base64.b64encode(encrypted).decode()

def decrypt_aes(text, key):
   aes = AES.new(pad(key), AES.MODE_ECB)
   decrypted = aes.decrypt(base64.b64decode(text)).decode().rstrip('\0')
   return decrypted

ca_root = "9a7e17e314233ba580574c418b8639350ff0a8132fa2aa3a69ec57e26e46e9d3" # Root CA

server_cert = "fc8f2f0b488c2572ad63fba4f5b75a8e3da0f3e10985b2cf55ec7eb011420daa" # Server cert

client_cert = "54e65e79498faf144592a834fec76af2088ad2b9faaa61c9a90fc988d0c2115c" # Client cert
 

ca_root = encrypt_aes(ca_root, hashlib.md5(platform.processor().encode()).hexdigest())

server_cert = encrypt_aes(server_cert, hashlib.md5(platform.processor().encode()).hexdigest())

client_cert = encrypt_aes(client_cert, hashlib.md5(platform.processor().encode()).hexdigest())