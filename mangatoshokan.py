#!/usr/bin/env python

"""
__version__ = "$Revision: 0.1 $"
__date__ = "$Date: 2009/02/16 $"
"""

import optparse
import urllib2
import urllib
import os
import sys
import re
import time
import gzip
import zipfile
import cStringIO

def main():
    cmd = optparse.OptionParser()
    cmd.add_option("-u", "--url", dest="url", help="URL")
    cmd.add_option("-f", "--file", dest="listfile", help="File")
    cmd.add_option("-c", "--chapter", type="int", dest="chapter", help="Chapter=int")
    cmd.add_option("-s", "--stop", type="int", dest="stop", help="Stop")
    cmd.add_option("-z", "--search", dest="search", help="Search")
    cmd.add_option("-d", "--debug", action="store_true", dest="debug", default=False)
    cmd.add_option("--zip", action="store_true", dest="zip", default=False)
    (options, args) = cmd.parse_args()
    manga = mangatoshokan(debug=options.debug, zip=options.zip)
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
            chapter = 0
            stop = 0
            if options.chapter:
                chapter = options.chapter
            if options.stop:
                stop = options.stop
            if stop and (stop < chapter):
                print ("start: %s stop: %s") % (str(chapter), str(stop))
                sys.exit(1)
            manga.getManga(options.url, chapter, stop)
    else:
        cmd.print_help()

class mangatoshokan:
    def __init__(self, debug=False, zip=False):
        #self.proxy = urllib2.ProxyHandler({'http': 'www-proxy.com:8080'})
        self.opener = urllib2.build_opener(urllib2.HTTPHandler(debuglevel=debug))
        self.opener.addheaders = [('User-Agent', 'Mozilla/4.0 (compatible; MSIE 7.0b; Windows NT 6.0)')] 
        self.prefix = "mangatoshokan"
        self.cache = "cache"
        self.zip = zip
        
    def getManga(self, url, chapter=0, stop=0):
        mainPage = "%s" % (url)
        self.log(mainPage)
        (html, headers) = self.openUrl(mainPage)
        infoTitle = re.compile('<title>([^:]+) ::').findall(html)
        self.log(infoTitle[0]) 
        chs = re.compile("<td width='40%' align='left' class='ccell'><a href='([^']+)'").findall(html)    
        totalPage = re.compile("<a href='([^']+)'>\d+</a>").findall(html)
        if len(totalPage) > 0:
            for sPage in range(len(totalPage) / 2): 
                self.log(totalPage[sPage])
                (html, headers) = self.openUrl(totalPage[sPage])
                chsTemp = re.compile("<td width='40%' align='left' class='ccell'><a href='([^']+)'").findall(html)
                self.log(len(chsTemp))
                if len(chsTemp) > 0:
                    for s in chsTemp:
                        chs.append(s)
        if chapter and (chapter > len(chs)):
            self.log("max chapter: %s" % (str(len(chs))))       
            sys.exit(1)
        chs.reverse()
        chsChapter = []
        for ch in chs:
            c = re.compile('([0-9\.]+)$').findall(ch)  
            if chapter and stop:
                if (float(c[0]) >= chapter) and (float(c[0]) <= stop):
                    chsChapter.append(ch)
            elif chapter and not stop:
                if (float(c[0]) >= chapter):
                    chsChapter.append(ch)
            elif not chapter and stop:
                if (float(c[0]) <= stop):
                        chsChapter.append(ch)
            else:
                chsChapter.append(ch)        
        for ch in range(0, len(chsChapter)):
            if not os.path.exists(self.prefix + chsChapter[ch]):
                os.makedirs(self.prefix + chsChapter[ch])
            if not os.path.exists(self.cache + '/' + self.prefix + chsChapter[ch]):
                os.makedirs(self.cache + '/' + self.prefix + chsChapter[ch])
            chUrl = "http://www.%s.com%s" % (self.prefix, chsChapter[ch])
            self.log(chUrl)
            (html, headers) = self.openUrl(chUrl)
            pageCount = re.compile('"(' + chsChapter[ch] + '/\d+)"(?: selected="selected")?>\d+</option>').findall(html)   
            gzip = False
            ext = 'html'       
            for pagen in range(0, len(pageCount)):
                self.log('Page: %s %s' % (pagen + 1, pageCount[pagen]))      
                if int(pagen) > 0:  
                    request = urllib2.Request('%s/%s' % (chUrl, pageCount[pagen].split('/')[-1]))
                    request.add_header('Accept-encoding', 'gzip')
                    page = self.opener.open(request)
                    #page = self.opener.open('%s%s.html' % (chUrl, pagen))
                    if page.headers.getheader('content-encoding') == 'gzip':
                        gzip = True
                        ext = 'gz'
                    else:
                        gzip = False
                        ext = 'html'
                    localFile = '%s/%s/%s/%s.%s' % (self.cache, self.prefix, chsChapter[ch].lstrip('/'), pageCount[pagen].split('/')[-1], ext) 
                    if os.path.exists(localFile):
                        if page.headers.getheader('Content-Length') and (long(page.headers.getheader('Content-Length')) == os.path.getsize(localFile)):
                            html = self.readFile(localFile)
                            self.log("skip %s" % (localFile))
                        else:
                            html = page.read()
                            self.writeFile(localFile, html)
                    else:
                        html = page.read()
                        self.writeFile(localFile, html)
                if gzip:
                    html = self.gunzip(cStringIO.StringIO(html))      
                imageHtml = re.compile('dir=\'rtl\'><img src="([^"]+)"').findall(html)   
                outFile = '%s/%s/%s' % (self.prefix, chsChapter[ch].strip('/'), imageHtml[0].split('/')[-1])
                print chsChapter[ch];sys.exit(1)
                if os.path.exists(outFile):
                    self.log("skip %s" % (outFile))
                    continue
                else:
                    self.log("download %s" % (outFile))
                    (image, header) = self.openUrl(imageHtml[0])    
                self.writeFile(urllib.unquote(outFile), image)
            if self.zip is True:
                zipName = self.prefix + "_"
                for name in chsChapter[ch].split('/'):
                    if name and (name != 'read'):
                        zipName += name + "_" 
                zipName = zipName.rstrip('_') + ".zip"
                self.createZip(dir=self.prefix + chsChapter[ch], zipName=zipName)

    def openUrl(self, url):
        request = urllib2.Request(url)
        request.add_header('Accept-encoding', 'gzip')
        retry = 1
        maxRetry = 4
        while retry < maxRetry:
            try:
                page = self.opener.open(request)
            except urllib2.URLError, e:
                self.log(e)
                self.log("(%s) %s" % (retry, request.get_full_url()))
                retry += 1
            else:
                retry = maxRetry
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
        
    def createZip(self, dir, zipName):
        if os.path.isdir(dir):
            self.log("creating %s" % (zipName))
            zip = zipfile.ZipFile(zipName, mode="w", compression=zipfile.ZIP_DEFLATED)  
            for item in os.listdir(dir):
                self.log("=> %s to %s" % (item, zipName))
                zip.write(dir + '/' + item)
            zip.close()
        
    def log(self, str):
        print "%s >>> %s" % (time.strftime("%x - %X", time.localtime()), str)
        
if __name__ == '__main__':
    main()
