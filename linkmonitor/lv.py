import util
import aiohttp
import asyncio
import discord
import re
import logging
import traceback
import time
import re
import random
import json
from urllib.parse import urljoin
from contextlib import asynccontextmanager
import random
import brotli

from datetime import datetime

webhook = 'https://discordapp.com/api/webhooks/746313524187365426/N8ZxHha8YxVko3NQrY5LcE7eHllcaK8JhW7clk1ho0YWMWoHp6qrsxCmVlxfXwbdbtBe'


screen_logger = logging.getLogger('screen_logger')
screen_logger.setLevel(logging.INFO)

streamFormatter = logging.StreamHandler()

streamFormatter.setFormatter(logging.Formatter('%(asctime)s %(message)s'))

fileFormatter = logging.FileHandler("lv.logs")

fileFormatter.setFormatter(logging.Formatter('%(asctime)s %(message)s'))

screen_logger.addHandler(streamFormatter)
screen_logger.addHandler(fileFormatter)


class invalid_status_code(Exception):
	"""exception if status code is not 200 or 404"""



def raise_for_status(response, skip = ()):
	if not (response.status == 200 or response.status == 404 or response.status in skip):
		print('raised for status')
		raise invalid_status_code('{} -> {}'.format(response.url, response.status))
	
def log_based_on_response(id, response):
	screen_logger.info("{} > {} -> {} " .format(id, str(response.url), response.status))
	#print(response.headers['server-timing'])

def log_exception(id, ex, *, traceback = True):
	print(ex)
	if traceback:
		screen_logger.debug("{} > {}".format(id, traceback.print_tb(ex.__traceback__)))
	screen_logger.info("{} > {}". format(id, str(ex)))



def get_title(sc):
    return re.search('<span class="productName">(.+?)<',sc).group(1).strip()
    

def get_image(sc):
    return re.search('r<div class="productImage">.<img data-src="(.+?)\?',sc , re.S).group(1).strip()

def get_price(sc):
	return re.search('"price": "(.+?)"',sc , re.S).group(1).strip()
 
class Monitor:
	def __init__(self, id, *, urlQueue,proxyBuffer, stock_info, session, image):
		self.urlQueue = urlQueue
		self.proxyBuffer = proxyBuffer
		self.stock_info = stock_info
		self.session = session
		self.first = True
		self.image = image
		self.instock = False
		self.variants = {}
		self.variantString = ''
		self.id = id
		self.onesize = False
		self.embed_sender = discord.embedSender(webhook)
	
	@asynccontextmanager
	async def load_url(self, *, wait):
		url = await self.urlQueue.get()
		try:
			yield url
		finally:
			self.urlQueue.put_nowait(url)
			await asyncio.sleep(wait)
	
	
	async def process_url(self,url,proxy):
		restocked =  False
		urlts = url +"?ts="+ str(time.time()) 
		
		sizes=[]
		instock = False
		current_stock_info = {}
		if self.first:
			async with self.session.get(urlts , proxy = proxy ) as response:
				response.text_content = await response.text()
			#responseklk=brotli.decompress(response.content)
			#print(response.text_content)
			log_based_on_response(self.id, response)
			raise_for_status(response)

			current_stock_info['title'] = get_title(response.text_content)
			current_stock_info['url'] = url
			current_stock_info['imgUrl'] = self.image
			current_stock_info['price'] =get_price(response.text_content)

			sizechart = re.search('<div class="sizesPanel js-tracking">(.+?)</div>',response.text_content, re.S)
			if sizechart is None:
				self.onesize= True
			else :
				self.onesize = False
				
			#print(sizechart)
			if not self.onesize:
				sizesDirty = re.findall( '<li(.+?)</li>',sizechart.group(1), re.S)
				for sizeD in sizesDirty:
					#print(sizesDirty)
					variant = re.search('data-sku="(.+?)"',sizeD).group(1).strip()
					size= re.search('class="name">(.+?)<',sizeD).group(1).strip()
					self.variants[variant]= size
					#print(self.variants)		
				variants = self.variants.keys()	
				variantString = ','.join(variants)
				print(variantString)	
				self.variantString= variantString
			
			else:
				sku = re.search('"sku": "(.+?)"',response.text_content).group(1).strip()
				self.variantString = sku

		
		urlapi = 'https://secure.louisvuitton.com/ajaxsecure/getStockLevel.jsp?storeLang=eng-us&pageType=storelocator_section&skuIdList=' + self.variantString
		#print(urlapi)
		
		async with self.session.get(urlapi , proxy = proxy ) as responseSizes:
			responseSizes.text_content = await responseSizes.text()
		#responseklk=brotli.decompress(response.content)
		#print(response.text_content)
		log_based_on_response(self.id, responseSizes)
		raise_for_status(responseSizes)
		
		log_based_on_response(self.id, responseSizes)
		raise_for_status(responseSizes)
		
		if not self.onesize:
			for variant in self.variants:
				if (variant + '":{"inStock":true') in responseSizes.text_content:
					print('found')
					sizes.append(self.variants[variant])
			#print(sizes)
		else:
			if 'inStock":true' in responseSizes.text_content:
				instock = True
				sizes = ['Restocked Only Size']


			else:
				instock = False
				sizes =['nosize']

		
		current_stock_info['sizes'] = sizes

		
		if(not self.first):
			#print(len(self.stock_info.get('sizes')))
			if not self.stock_info.get('onesize'):
				if self.stock_info.get('sizes') != current_stock_info.get('sizes') and len(self.stock_info.get('sizes'))<=len(current_stock_info.get('sizes')):
						restocked = True
			else: 
				if instock != self.instock and instock==True:
					restocked=True
			
			current_stock_info['title'] =self.stock_info['title']
			current_stock_info['url'] = self.stock_info['url']
			current_stock_info['imgUrl'] = self.stock_info['imgUrl']
			current_stock_info['price'] = self.stock_info['price']

		if restocked:
			screen_logger.info("{} > {} Restocked Sizes".format(self.id, url))
						
			embed = discord.make_embed(current_stock_info)
			#print(embed)
			if await self.embed_sender.send(embed):
				screen_logger.info("{} > **Discord Notification Sent for {}**".format(self.id, url))
			else:
				screen_logger.info("{} > **Discord Notification Failed for {}**".format(self.id, url))

		self.stock_info = current_stock_info	
		self.first = False

	async def start(self, wait):
		proxy = await self.proxyBuffer.get_and_inc()
		
		screen_logger.info('{} > Using Proxy {}'.format(self.id, proxy))
		
		while True:
			async with self.load_url(wait = wait) as url:
				#screen_logger.info(f"{self.id} > Checking {url}")
				for i in range(2):
					try:
						await self.process_url(url, proxy)
						break
					except Exception as e:
						log_exception(self.id, e, traceback = False)
					
						if i == 1:
							proxy = await self.proxyBuffer.get_and_inc()
							screen_logger.info('{} > Changing Proxy to {}'.format(self.id, proxy))








async def main(urls,proxies, workers, wait_time, images):
	#queries = [{'url': link, 'previousStockedSizes': []} for link in queries]
	
	proxyBuffer = util.readOnlyAsyncCircularBuffer(proxies)
	
	urlQueue = asyncio.Queue()
	
	for url in urls:
		urlQueue.put_nowait(url)
	

	headers = {
	'authority': 'us.louisvuitton.com',
	'method': 'GET',
	'scheme': 'https',
	'accept': ' text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
	'accept-encoding': ' gzip, deflate',
	'accept-language': ' es,ca;q=0.9,en;q=0.8,de;q=0.7',
	'cache-control': ' max-age=0',
	'sec-fetch-dest': ' document',
	'sec-fetch-mode': ' navigate',
	'sec-fetch-site': ' same-origin',
	'sec-fetch-user': ' ?1',
	'upgrade-insecure-requests': ' 1',
	'user-agent': ' Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36'
	}

	timeout = aiohttp.ClientTimeout(total = 8)
	
	stock_info = {}

	session = aiohttp.ClientSession(headers = headers, timeout = timeout, cookie_jar = aiohttp.DummyCookieJar() )
	
	monitors = [Monitor(f'worker-{i}', stock_info = stock_info, session = session, urlQueue = urlQueue ,proxyBuffer = proxyBuffer, image = images[i]) for i in range(workers)]
	
	coros = [monitor.start(wait = wait_time) for monitor in monitors]
	
	await asyncio.gather(*coros)
	
	await     session.close()
		
if __name__ == "__main__":
	
	url_file = 'urls.txt'
	proxy_file = 'proxies.txt'
	image_file = 'images.txt'
	
	images = util.nonblank_lines(image_file)
	urls = util.nonblank_lines(url_file)
	
	proxies = util.load_proxies_from_file(proxy_file, shuffle = True)

	workers = len(urls)
	wait_time = 3


	#policy = asyncio.WindowsSelectorEventLoopPolicy()
	#asyncio.set_event_loop_policy(policy)

	asyncio.run(main(urls, proxies, workers, wait_time, images))
