#!/usr/bin/env python

from base45 import b45decode, b45encode
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto import Hash

import sys

import qrcode

contact = sys.argv[1]

key = RSA.importKey(open('stuss2021_key.pub').read())
cipher = PKCS1_OAEP.new(key, hashAlgo=Hash.SHA256)

msg = b45encode(cipher.encrypt(bytes(contact.encode())))

print('Contact: {}\nBase45: {}'.format(contact, msg))

qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_Q,
    box_size=10,
    border=4,
)
qr.add_data(msg)
qr.make(fit=True)

img = qr.make_image(fill_color="black", back_color="white")
img.show()
