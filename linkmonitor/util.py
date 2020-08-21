import asyncio
import random
import itertools
import os

def nonblank_lines(filename):
	with open(filename) as f:
		stripped_lines = [line.strip() for line in f]
		print(stripped_lines)
		return [line for line in stripped_lines if line]



def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)		

def load_proxies_from_file(filename, shuffle = True):
	proxies = nonblank_lines(filename)
	
	if shuffle:
		random.shuffle(proxies)
	result = []
	
	for proxy in proxies:
		proxyTokens = proxy.split(':')
		
		proxyStr = ":".join(proxyTokens[0:2])
		
		if len(proxyTokens) == 4:
			proxyStr = ":".join(proxyTokens[2:]) + "@" + proxyStr
		
		result.append('http://' + proxyStr)
	return result

class readOnlyAsyncCircularBuffer:
	def __init__(self, data):
		assert len(data) > 0
		self.data = list(data)
		self.lock = asyncio.Lock()
		self.index = 0
	
	async def get(self):
		async with self.lock:
			return self.data[self.index]
	
	async def get_and_inc(self):
		async with self.lock:
			oIndex = self.index
			self.index = (self.index + 1) % len(self.data)
			return self.data[oIndex]

async def safe_get(session, *args, **kwargs):
	
	for _ in range(2):
		async with session.get(*args, **kwargs) as response:
			response.text_content = await response.text()
			if response.status == 200 or response.status == 404:
				break
	return response