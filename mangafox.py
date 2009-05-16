#!/usr/bin/python

"""
__version__ = "$Revision: 0.1 $"
__date__ = "$Date: 2009/05/03 $"
"""

import optparse
import urllib2
import os
import sys
import re
import time

def main():
	cmd = optparse.OptionParser()
	cmd.add_option("-u", "--url", dest="url", help="URL")
	cmd.add_option("-f", "--file", dest="listfile", help="File")
	(options, args) = cmd.parse_args()
	manga = mangafox()
	if options.listfile and (options.listfile is not None):
		try:
			listFile = file(options.listfile, 'r')
		except IOError, e:
			print e
			sys.exit(1)
		items = listFile.readlines()
		for item in items:
			item.lstrip()
			if (item[0] == '#' or item[0] == ';'):
				continue
			item = re.sub('\n|\r', '', item)
			manga.getManga(item)
	elif options.url and (options.url is not None):
		if re.compile('http://').findall(options.url):
			manga.getManga(options.url)
	else:
		cmd.print_help()

class mangafox:
	def __init__(self):
		#self.proxy = urllib2.ProxyHandler({'http': 'www-proxy.com:8080'})
		self.opener = urllib2.build_opener()
		self.opener.addheaders = [('User-Agent', 'Mozilla/4.0 (compatible; MSIE 7.0b; Windows NT 6.0)')]	
		self.prefix = "mangafox"
		self.cache = ".cache"
		
	def getManga(self, url):
		mainPage = "%s%s" % (url, '?no_warning=1')
		self.log(mainPage)
		(html, headers) = self.openUrl(mainPage)
		infoTitle = re.compile('<h2>([^>]+)</h2>').findall(html)
		self.log(infoTitle[0])
		chs = re.compile('class="edit">edit</a>\s+?<a href="([^"]+)" class="chico">').findall(html)
		chs.reverse()
		for ch in range(0, len(chs)):
			if not os.path.exists(chs[ch].lstrip('/')):
				os.makedirs(chs[ch].lstrip('/'))
			if not os.path.exists(self.cache + chs[ch]):
				os.makedirs(self.cache + chs[ch])
			chUrl = "http://www.%s.com%s" % (self.prefix, chs[ch])
			self.log(chUrl)
			(html, headers) = self.openUrl(chUrl)
			pageCount = re.compile('<option value="\d+"[^>]+?>(\d+)</option>').findall(html)
			for pagen in range(1, (len(pageCount) / 2) + 1):
				self.log('Page: %s %s%s.html' % (pagen, chUrl, pagen))
				if int(pagen) > 1:
					localFile = '%s%s%s.html' % (self.cache, chs[ch], pagen)
					page = self.opener.open('%s%s.html' % (chUrl, pagen))
					if os.path.exists(localFile):
						if page.headers.items()[0][1].isdigit():
							if long(page.headers.items()[0][1]) == os.path.getsize(localFile):
								html = self.readFile(localFile)
							else:
								html = page.read()
								self.writeFile(localFile, html)
						else:
							html = page.read()
							self.writeFile(localFile, html)
					else:
						html = page.read()
						self.writeFile(localFile, html)
				imageHtml = re.compile(';"><img src="([^"]+)" width="\d+" id="image"').findall(html) 
				outFile = '%s/%s' % (chs[ch].strip('/'), imageHtml[0].split('/')[-1])
				if os.path.exists(outFile):
					self.log("skip %s" % (outFile))
					continue
				else:
					self.log("download %s" % (outFile))
					(image, header) = self.openUrl(imageHtml[0])			
				self.writeFile(outFile, image)

	def openUrl(self, url):
		page = self.opener.open(url)	
		html = page.read()
		return(html, page.headers.items())
	
	def writeFile(self, filename, content):
		fileCache = file(filename, 'wb')
		fileCache.write(content)
		fileCache.close()
		
	def readFile(self, filename):
		fileCache = file(filename, 'rb')
		content = fileCache.read()
		fileCache.close()
		return content
		
	def log(self, str):
		print "%s >>> %s" % (time.strftime("%x - %X", time.localtime()), str)
		
if __name__ == '__main__':
	main()
