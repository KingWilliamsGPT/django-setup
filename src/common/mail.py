class Email:
	def __init__(self, token, subject, from_, from_name, to, attachmentFiles={}, replyTo=None, replyToName=None, html=None, text_message=None):
		self.token=token
		self.subject = subject
		self.from_ = from_
		self.from_name = from_name
		self.to = to
		self.replyTo = replyTo
		self.replyToName = replyToName
		self.html = html
		self.text_message = text_message
		self.attachmentFiles = attachmentFiles




def send(email, isImportant=True):
	'''
		isImportant: for campaigns use False


	.............................................
	the following are usefull for campaign purposes
		trackOpens (optional) and trackClicks (optional): These parameters allow you to enable or disable open and click tracking for your emails.
		trackOpens: If enabled (True), it will track whether recipients open the email. This can be a helpful metric for understanding engagement rates.
		trackClicks: If enabled (True), it will track whether recipients click on any links within the email body. This provides valuable data on user interaction with your email content.
		utmSource, utmMedium, utmCampaign, utmContent (optional): These parameters are essential for tracking purposes in marketing campaigns. They allow you to define UTM tags that will be appended to links within your email. These tags can then be used by analytics tools to track the source, medium, campaign, and content associated with your email clicks.
	'''
	from src.common.ElasticEmailClient import ApiClient, Email     
	ApiClient.apiKey = email.token

	return Email.Send(
            subject=email.subject,                             
            EEfrom=email.from_,
            fromName=email.from_name,
            sender=email.from_,	# Some mail servers might reject emails where the from address is different from the sender address. It's generally recommended to keep them the same to avoid deliverability issues
            senderName=email.from_name,
            msgFrom=email.from_, #It's rarely used and typically left as the same as from
            msgFromName=email.from_name,
        	replyTo=email.replyTo,
        	replyToName=email.replyToName,
        	to=email.to,
        	bodyHtml=email.html,
        	bodyText=email.text_message,
        	isTransactional=isImportant, # if true gives more priority, for non-commercial purposes
        	attachmentFiles=email.attachmentFiles,  # array of tuples = ('file_name', b'byte_content')
        )


def test():
	from django.conf import settings
	token = settings.ELASTIC_EMAIL_KEY
	sender_name = settings.ELASTIC_EMAIL_NAME
	sender_email = settings.ELASTIC_EMAIL
	# email = Email(
	# 	token=token,
	# 	subject="Subject",
	# 	from_="williamusanga23@gmail.com",
	# 	from_name="AutoVerify",
	# 	to={"williamusanga22@gmail.com"},
	# 	html="Hi this is an <b>important</b> message",
	# )
	email = Email(
		token=token,
		subject="Subject to send",
		from_=sender_email,
		from_name="AutoVerify",
		to={"williamusanga22@gmail.com"},
		html="Hi this is an <b>important</b> message",
	)
	return send(email)


def send_html(subject, msg, to=(), attachmentFiles={}):
	from django.conf import settings
	token = settings.ELASTIC_EMAIL_KEY
	sender_name = settings.ELASTIC_EMAIL_NAME
	sender_email = settings.ELASTIC_EMAIL

	email = Email(
		token=token,
		subject=subject,
		from_=sender_email,
		from_name=sender_name,
		to=to,
		html=msg,
		attachmentFiles=attachmentFiles,
	)
	return send(email)


# from src.common.ElasticEmailClient import Email as E_Email
# res = test()
# r =  E_Email.Status(res["messageid"])
