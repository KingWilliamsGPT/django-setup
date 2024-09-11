import base64
import os.path
import requests
import json
import threading
from pprint import pprint



UNSUPPORTED_ATTACHMENT_FORMATS = ['ade','adp','bat','chm','cmd','com','cpl','exe','hta','ins','isp','js','jse','lib','lnk','mde','msc','msp','mst','pif','scr','sct','shb','sys','vb','vbe','vbs','vxd','wsc','wsf','wsh','app','asp','bas','cer','cnt','crt','csh','der','fxp','gadget','hlp','hpj','inf','ksh','mad','maf','mag','mam','maq','mar','mas','mat','mau','mav','maw','mda','mdb','mdt','mdw','mdz','msh','msh1','msh2','msh1xml','msh2xml','msi','msp','ops','osd','pcd','plg','prf','prg','pst','reg','scf','shs','ps1','ps1xml','ps2','ps2xml','psc1','psc2','tmp','url','vbp','vsmacros','vsw','ws','xnk']


class MimeTypeError(TypeError):
	'''Occurs usually when an invalid mime type is passed for attachments'''


def _post(url, headers, payload):
	# headers:dict
	# payload:dict
	return requests.post(url, headers=headers, json=payload)


def _safe_set(key, value, dict_):
	if(value):
		dict_[key] = value
	return dict_

def _check_mime_type(mime_type):
	if not mime_type.is_valid():
		raise MimeTypeError(f'Unsupported mime_type {mime_type}')
	return mime_type


class MimeType:
	def __init__(self, format="", klass=""):
		self.format = format
		self.klass = klass

	def is_valid(self):
		return self.format not in UNSUPPORTED_ATTACHMENT_FORMATS

	@property
	def value(self):
	    return f"{self.klass} / {self.format}"

	def __str__(self):
		return f"<MimeType: format={self.format}, klass={self.klass}>"

	def __bool__(self):
		return bool(self.format and self.klass)



class Config:
	api_key = None
	headers = None
	zepto_url = "https://api.zeptomail.com/v1.1/email"
	# zepto_url = "https://httpbin.org/post" # test server


	def __init__(self, api_key, headers=None, _test_mode=False):
		self.api_key = api_key
		self.headers = headers or {}
		self._test_mode = _test_mode

		self.update_headers(
			{
				"Accept": "application/json",
				"Content-Type": "application/json",
				"Authorization":f"Zoho-enczapikey {api_key}",
			}
		)


	def update_headers(self, kw, force=False):
		for key, value in kw.items():
			if force:
				self.headers[key] = value
			else:
				self.headers.setdefault(key, value)



class Email:

	DEFAULT_MIME_TYPE = MimeType("text", "plain")

	def __init__(self, config, bounce_address=None):
		# bouncee address should usually be the seller"s address
		self.config = config
		self.bounce_address = bounce_address


	def send(self, from_, from_name, to, subject, text_body=None, html_body=None, reply_to=(),  attachments=(), client_reference=None):
		"""
			replyTo: [("example.gmail.com", "john doe"), ...]
			attachments: [("base64_string", <MimeType>, "john doe"), ...]
		"""
		# https://www.zoho.com/zeptomail/help/api/email-sending.html
		payload = {
			"subject": subject,
			"from": {
		        "address": from_,
		        "name": from_name,
		    },
			"to": [
		        {
		            "email_address": {
		                "address": email,
		                "name": f"TO_{index}"
		            }
		        } for index, email in enumerate(to)
		    ],
		}
		_safe_set("bounce_address", self.bounce_address, payload)
		_safe_set("reply_to", [
				{
					"address":email,
					"name":name,
				} for email, name in reply_to
			],
			payload
		)
		_safe_set("textbody", text_body, payload)
		_safe_set("htmlbody", html_body, payload)
		_safe_set("client_reference", client_reference, payload)
		_safe_set("attachments", [
				{
					"content": content,
					"mime_type": (_check_mime_type(mime_type) or self.DEFAULT_MIME_TYPE).value,
					"name": name, 
					# "file_cache_key": file_cache_key,
				} for content, mime_type, name in attachments
			], payload)

		if self.config._test_mode:
			return payload

		self._payload = payload

		return _post(
			url=self.config.zepto_url,
			payload=payload,
			headers=self.config.headers,
		)


def bytes_to_base64(byte_string):
    """
    Converts a byte string to its base64-encoded version.
    
    Args:
    byte_string (bytes): The byte string to be encoded.
    
    Returns:
    str: The base64-encoded string.
    """
    # Encode the byte string to base64
    base64_encoded = base64.b64encode(byte_string)
    
    # Convert the base64 bytes to a string and return
    return base64_encoded.decode('utf-8')


def test1():
	from pprint import pprint
	api_key = "test_api_key..."
	bounce_address = "example@gmail.com"
	config = Config(api_key, _test_mode=True)
	email = Email(config, bounce_address)
	res = email.send(
		from_="from@gmail.com",
		from_name="from_name",
		to=("mail1@mail.com", "mail1@mail.com",),
		subject="subject",
		text_body="text_body",
		html_body="html_body",
		reply_to=("reply_mail1@mail.com", "reply_mail1@mail.com",),
		attachments=[("base64string...", MimeType(), "name")],
		client_reference="transaction_id",
	)
	pprint(res)


def test2():
	from django.conf import settings

	api_key = settings.ZEPTO_API_KEY
	bounce_address = settings.ZEPTO_EMAIL
	config = Config(api_key)
	email = Email(config)
	# return email
	res = email.send(
		from_=settings.ZEPTO_EMAIL,
		from_name=settings.ZEPTO_EMAIL_NAME,
		to=("williamusanga23@gmail.com", ),
		subject="TEST_SUBJECT",
		# text_body="TEST_BODY",
		html_body="HTML_BODY",
		# reply_to=("williamusanga22@gmail.com",),
		# attachments=[("base64string...", MimeType(), "name")],
		# client_reference="transaction_id_34343434",
	)
	pprint(res)
	return email, res


def test_send_file(path, mime_type, email):
	# >>> test_send_file("/path/to/some/file", "application/zip")
	with open(path, "rb") as file:
		contents = file.read()
	
	attachments = [(bytes_to_base64(contents), MimeType(*reversed(mime_type.split("/", 2))), os.path.basename(path))]
	return _send(subject="A file", text_body="Text Body", to=(email,))


def _send(bounce_address=None, to=(), subject=None, text_body=None, html_body=None, reply_to=(),  attachments=(), client_reference=None, thread=True):
	from django.conf import settings

	api_key = settings.ZEPTO_API_KEY
	bounce_address = bounce_address

	config = Config(api_key)
	email = Email(config, bounce_address)

	def send_email():
		try:
			email.send(
				from_=settings.ZEPTO_EMAIL,
				from_name=settings.ZEPTO_EMAIL_NAME,
				to=to,
				subject=subject,
				text_body=text_body,
				html_body=html_body,
				reply_to=reply_to,
				attachments=attachments,
				client_reference=None
			)
		except Exception as ex:
			print("error while trying to thread sending an email")
			print(ex)
			raise

	if thread:
		threading.Thread(target=send_email).start()
	else:
		send_email()



if __name__ == "__main__":
	test1()


