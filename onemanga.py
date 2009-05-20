#!/usr/bin/env python

"""
__version__ = "$Revision: 0.1 $"
__date__ = "$Date: 2009/05/03 $"
"""

import optparse
import urllib2
import urllib
import os
import sys
import re
import time
import gzip
import cStringIO

def main():
	cmd = optparse.OptionParser()
	cmd.add_option("-u", "--url", dest="url", help="URL")
	cmd.add_option("-f", "--file", dest="listfile", help="File")
	cmd.add_option("-c", "--chapter", dest="chapter", type="int", help="Chapter")
	cmd.add_option("-s", "--stop", dest="stop", type="int", help="Stop")
	cmd.add_option("-z", "--search", dest="search", help="Search")
	cmd.add_option("-d", "--debug", action="store_true", dest="debug", default=False)
	(options, args) = cmd.parse_args()
	manga = onemanga(options.debug)
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
	elif options.search and (options.search is not None):
		manga.searchManga(options.search)
	else:
		cmd.print_help()

class onemanga:
	def __init__(self, debug=False):
		#self.proxy = urllib2.ProxyHandler({'http': 'www-proxy.com:8080'})
		self.opener = urllib2.build_opener(urllib2.HTTPHandler(debuglevel=debug))
		self.opener.addheaders = [('User-Agent', 'Mozilla/4.0 (compatible; MSIE 7.0b; Windows NT 6.0)')]	
		self.prefix = "onemanga"
		self.cache = "cache"
		
	def getManga(self, url, chapter=0, stop=0):
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
				if (float(ch[0].split('/')[-2]) >= chapter) and (float(ch[0].split('/')[-2]) <= stop):
					chsChapter.append(ch)
			elif chapter and not stop:
				if (float(ch[0].split('/')[-2]) >= chapter):
					chsChapter.append(ch)
			elif not chapter and stop:
				if (float(ch[0].split('/')[-2]) <= stop):
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
			gzip = False
			ext = 'html'
			for pagen in range(0, len(pageCount)):
				self.log('%s Page: %s %s%s/' % (infoChapter[0][1].strip(), pageCount[pagen], chUrl, pageCount[pagen]))
				if int(pagen) > 0:
					#page = self.opener.open('%s%s/' % (chUrl, pageCount[pagen]))
					request = urllib2.Request('%s%s/' % (chUrl, pageCount[pagen]))
					request.add_header('Accept-encoding', 'gzip')
					page = self.opener.open(request)
					if page.headers.getheader('content-encoding') == 'gzip':
						gzip = True
						ext = 'gz'
					else:
						gzip = False
						ext = 'html'
					localFile = "%s/%s%s%s.%s" % (self.cache, self.prefix, subPage[0], pageCount[pagen], ext)
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
				if gzip:
					html = self.gunzip(cStringIO.StringIO(html))
				imageHtml = re.compile('<input type="hidden" name="img_url" value="([^"]+)" />').findall(html) 
				outFile = '%s%s%s' % (self.prefix, subPage[0], imageHtml[0].split('/')[-1])
				if os.path.exists(outFile):
					self.log("skip %s" % (outFile))
					continue
				else:
					self.log("download %s" % (outFile))
					(image, header) = self.openUrl(imageHtml[0])			
					self.writeFile(outFile, image)
					
	def searchManga(self, search):
		s = {"series_name": search, "author_name": "", "artist_name": ""}
		url = "http://feedback.%s.com/directory/search/" % (self.prefix)
		(html, headers) = self.openUrl(url, urllib.urlencode(s))
		if '<tr class="bg01">' in html:
			result = re.compile('<td class="ch-subject"><a href="([^"]+)"\s?>([^<]+)</a>').findall(html)
			if result:
				c = 0
				for item in result:
					c += 1
					shttp = "http://www.%s.com%s" % (self.prefix, item[0])
					print "%03d. %s: %s" % (c, item[1], shttp)
			else:
				print "No matches found."
		else:
			print "No matches found."		
						
	def openUrl(self, url, data=None):
		request = urllib2.Request(url)
		request.add_header('Accept-encoding', 'gzip')
		page = self.opener.open(request, data)
		html = page.read()
		if page.headers.getheader('content-encoding') == 'gzip':
			html = self.gunzip(cStringIO.StringIO(html))
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

	def gunzip(self, fileobj):
		g = gzip.GzipFile(fileobj=fileobj)
		gFile = g.read()
		g.close()
		return gFile
	
	def log(self, str):
		print "%s >>> %s" % (time.strftime("%x - %X", time.localtime()), str)
		
if __name__ == '__main__':
	main()
