import aiohttp
from datetime import datetime
import asyncio
import json
import util

def make_embed(details):


	#print(details)
	
	if len(details['sizes'])>1:
		separator='\n'
		sizes = separator.join(details['sizes'])
	else:
		sizes = details['sizes'][0]
	#QUICKTASKS CONFIG
	"""
	quicktasks = []
	orbitUrl = 'http://localhost:5060/quicktask?site=kickz&method=url&input=' + details['url']
	t3kUrl = 'https://api.t3k.industries/qt/?module=kickz&input=' + details['url']
	
	orbit = "[{}]({}) ".format( "ORBIT", orbitUrl)	
	t3k = "[{}]({}) ".format( "T3K", t3kUrl)	
	quicktasks.append({
		'name': 'QT',
		'value': orbit + t3k
	})
	"""

	#print(details)
	return [{
				
				'title': "{}\n".format(details['title']),
				'url': details['url'],
				'color': 0x8c7656,
				'thumbnail': {
					'url': details['imgUrl']
					},
				'fields': [
							{
								"name": "Price",
								"value": details['price']
,
							},
							{
								"name": "Sizes",
								"value": sizes
,
							},
							],
			'footer': {
				'icon_url': 'https://pbs.twimg.com/profile_images/1268224680697225216/6WiKMaJl_400x400.jpg',   # add cookgroup photo
				'text': 'LV monitor by SabreIO'               #change to cg
				}
			}]

class embedSender:
	def __init__(self, webhook, wait_time_on_error = 4):
		self.webhook = webhook
		self.session = aiohttp.ClientSession(cookie_jar = aiohttp.DummyCookieJar())
		self.wait_time_on_error = wait_time_on_error
		
	async def send(self, embed):
		
		data = {
			'username' : 'Louis Vuitton', # add monitor name
			'avatar_url': 'https://pbs.twimg.com/profile_images/1268224680697225216/6WiKMaJl_400x400.jpg', #add webstore photo
			'embeds': embed
		}
		for _ in range(2):
			async with self.session.post(self.webhook, json = data) as resp:
				if resp.status == 204:
					break
			
			await asyncio.sleep(self.wait_time_on_error)
		return resp.status == 204
