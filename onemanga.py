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
	cmd.add_option("-c", "--chapter", dest="chapter", type="int", help="Chapter")
	cmd.add_option("-s", "--stop", dest="stop", type="int", help="Stop")
	(options, args) = cmd.parse_args()
	manga = onemanga()
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
		chapter = 0
		stop = 0
		if options.chapter:
			chapter = options.chapter
		if options.stop:
			stop = options.stop
		if stop and (stop < chapter):
			print ("start: %s stop: %s") % (str(chapter), str(stop))
			sys.exit(1)
		if re.compile('http://').findall(options.url):
			manga.getManga(options.url, chapter, stop)
	else:
		cmd.print_help()

class onemanga:
	def __init__(self):
		#self.proxy = urllib2.ProxyHandler({'http': 'www-proxy.com:8080'})
		self.opener = urllib2.build_opener()
		self.opener.addheaders = [('User-Agent', 'Mozilla/4.0 (compatible; MSIE 7.0b; Windows NT 6.0)')]	
		self.prefix = "onemanga"
		self.cache = "cache"
		
	def getManga(self, url, chapter, stop):
		mainPage = url
		self.log(mainPage)
		(html, headers) = self.openUrl(mainPage)
		infoTitle = re.compile('Title: <span class="series-info">([^<]+)</span><br />').findall(html)
		self.log(infoTitle[0])
		chs = re.compile('<td class="ch-subject"><a href="([^"]+)">([^<]+)</a></td>').findall(html)
		if chapter and (chapter > len(chs)):
			self.log("max chapter: %s" % (str(len(chs)))) 		
			sys.exit(1)
		chs.reverse()
		chsChapter = []
		for ch in chs:
			if chapter and stop:
				if (float(ch[1].split()[-1]) >= chapter) and (float(ch[1].split()[-1]) <= stop):
					chsChapter.append(ch)
			elif chapter and not stop:
				if (float(ch[1].split()[-1]) >= chapter):
					chsChapter.append(ch)
			elif not chapter and stop:
				if (float(ch[1].split()[-1]) <= stop):
					chsChapter.append(ch)
			else:
				chsChapter.append(ch)
		for ch in chsChapter:
			chUrl = "http://www.%s.com%s" % (self.prefix, ch[0])
			self.log(chUrl)
			(html, headers) = self.openUrl(chUrl)
			infoChapter = re.compile(' <h1><a href="/">OM</a> / <a href="/[^/]+/">([^<]+)</a> /([^<]+)</h1>').findall(html)
			infoChapterTitle = re.compile('<p>Chapter Title: ([^<]+)</p>').findall(html)
			self.log("%s %s: %s" % (infoChapter[0][0].strip(), infoChapter[0][1].strip(), infoChapterTitle[0].strip()))
			subPage = re.compile('<ul>\s+?<li><a href="([^"]+)">[^<]+</a>\.</li>').findall(html)			
			if not os.path.exists(self.prefix + subPage[0]):
				os.makedirs(self.prefix + subPage[0])
			if not os.path.exists(self.cache + '/' + self.prefix + subPage[0]):
				os.makedirs(self.cache + '/' + self.prefix + subPage[0])
			subChUrl = "http://www.%s.com%s" % (self.prefix, subPage[0])
			self.log(subChUrl)
			(html, headers) = self.openUrl(subChUrl)
			pageCount = re.compile('<option value="([^"]+)"[^>]+?>[^<]+</option>').findall(html)
			for pagen in range(0, len(pageCount)):
				self.log('%s Page: %s %s%s/' % (infoChapter[0][1].strip(), pageCount[pagen], chUrl, pageCount[pagen]))
				if int(pagen) > 0:
					localFile = "%s/%s%s%s.html" % (self.cache, self.prefix, subPage[0], pageCount[pagen])
					page = self.opener.open('%s%s/' % (chUrl, pageCount[pagen]))
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
				imageHtml = re.compile('<input type="hidden" name="img_url" value="([^"]+)" />').findall(html) 
				outFile = '%s%s%s' % (self.prefix, subPage[0], imageHtml[0].split('/')[-1])
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
